"""
risk_surface_service.py

Serviço responsável por gerar e persistir a "superfície de risco" (risk surface)
para um município e um snapshot_timestamp (bucket global), usando Kernel Gaussiano.

Objetivo:
- A partir dos snapshots pontuais (ICRA por ponto), gerar uma superfície contínua
  (grid + kernel) e persistir como GeoJSONB (PostgreSQL) em risk_surfaces.

Regras/Arquitetura:
- Service decide se recalcula ou reutiliza (repository filtra validade quando solicitado).
- Repository cuida de persistência e consultas.
- Sem mocks/dados simulados: tudo real e pronto para produção.
- Datetimes sempre UTC / timezone-aware.
- Grid filtrado pelo polígono do município (mais robusto que bounding box puro).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from bisect import bisect_right
from math import cos, radians, sin, asin, sqrt
from typing import Any, Dict, List, Optional, Tuple, Callable

from sqlalchemy.orm import Session

from backend.app.settings import settings
from backend.app.models.point import Point
from backend.app.models.risk_snapshot import RiskSnapshot
from backend.app.models.municipality import Municipality
from backend.app.models.risk_surface import RiskSurface

from backend.app.repositories.municipality_repository import MunicipalityRepository
from backend.app.repositories.risk_surface_repository import RiskSurfaceRepository
from backend.app.repositories.risk_repository import RiskRepository

try:
    from shapely.geometry import shape as shapely_shape
    from shapely.geometry import Point as ShapelyPoint
    from shapely.prepared import prep as shapely_prep
except Exception: 
    shapely_shape = None
    ShapelyPoint = None
    shapely_prep = None


# ============================================================
# EXCEÇÕES
# ============================================================

class RiskSurfaceServiceError(RuntimeError):
    """Erro ao gerar/obter superfície de risco."""


# ============================================================
# CONFIG / DTOs
# ============================================================

@dataclass(frozen=True)
class SurfaceConfig:
    grid_resolution_m: int
    knn_k: int
    sigma_min_m: int
    sigma_max_m: int
    sigma_scale: float  
    high_risk_threshold: float
    t_baixo: float
    t_moderado: float
    t_alto: float
    max_cells: int


# ============================================================
# SERVICE
# ============================================================

class RiskSurfaceService:
    """
    Gera e persiste superfícies de risco (grid + kernel).
    """

    def __init__(
        self,
        municipality_repo: MunicipalityRepository,
        surface_repo: RiskSurfaceRepository,
        risk_repo: RiskRepository,
    ) -> None:
        self.municipality_repo = municipality_repo
        self.surface_repo = surface_repo
        self.risk_repo = risk_repo

        self.cfg = self._load_config()

    # --------------------------------------------------------
    # PÚBLICO
    # --------------------------------------------------------

    def get_or_generate_surface(
        self,
        db: Session,
        municipality_id: int,
        snapshot_timestamp: datetime,
        force_recompute: bool = False,
        source: str = "auto",  # auto | on_demand | scheduled
    ) -> RiskSurface:
        """
        Retorna superfície do município no timestamp (bucket).

        - Se existir e estiver válida (valid_until) e force=False => reutiliza.
        - Caso contrário => recalcula e salva.
        """
        if snapshot_timestamp.tzinfo is None:
            snapshot_timestamp = snapshot_timestamp.replace(tzinfo=timezone.utc)
        else:
            snapshot_timestamp = snapshot_timestamp.astimezone(timezone.utc)

        if not force_recompute:
            existing = self.surface_repo.get_by_municipality_and_timestamp(
                municipality_id=municipality_id,
                snapshot_timestamp=snapshot_timestamp,
            )
            if existing and self.surface_repo.is_valid(existing, now=self._utcnow()):
                return existing

        municipality = self.municipality_repo.get_by_id(municipality_id)
        if not municipality or not municipality.active:
            raise RiskSurfaceServiceError(f"Município inválido ou inativo: {municipality_id}")

        points = (
            db.query(Point)
            .filter(Point.active.is_(True))
            .filter(Point.municipality_id == municipality_id)
            .order_by(Point.id.asc())
            .all()
        )

        if not points:
            raise RiskSurfaceServiceError(
                f"Nenhum ponto ativo encontrado para municipality_id={municipality_id}"
            )

        bucket_snaps = self.risk_repo.get_snapshots_by_bucket(snapshot_timestamp=snapshot_timestamp)
        snap_by_point = {s.point_id: s for s in bucket_snaps}

        valid_points: List[Point] = []
        valid_snaps: List[RiskSnapshot] = []
        for p in points:
            s = snap_by_point.get(p.id)
            if s is not None:
                valid_points.append(p)
                valid_snaps.append(s)

        if not valid_points:
            raise RiskSurfaceServiceError(
                f"Nenhum snapshot disponível para os pontos do município no bucket={snapshot_timestamp.isoformat()}"
            )

        valid_sources = {"on_demand" , "scheduled", "auto"}
        surface = self._generate_surface(
            municipality=municipality,
            points=valid_points,
            snapshots=valid_snaps,
            snapshot_timestamp=snapshot_timestamp,
            source=source if source in valid_sources else "on_demand",
        )

        if force_recompute:
            saved = self.surface_repo.replace_surface(surface)
        else: saved = self.surface_repo.save_surface(surface)

        return saved

    # --------------------------------------------------------
    # GERAÇÃO (core)
    # --------------------------------------------------------

    def _generate_surface(
        self,
        municipality: Municipality,
        points: List[Point],
        snapshots: List[RiskSnapshot],
        snapshot_timestamp: datetime,
        source: str,
    ) -> RiskSurface:
        # 1) Preparar geometria municipal e grid
        geom = self._extract_geometry(municipality.geojson)
        bbox = self._bbox_from_geometry(geom)

        grid = self._generate_grid(
            bbox=bbox,
            geometry=geom,
            resolution_m=self.cfg.grid_resolution_m,
            max_cells=self.cfg.max_cells,
        )

        # 2) Sigma adaptativo por ponto
        #    sigma_i calculado a partir da distância média dos k vizinhos mais próximos
        #    (densidade alta => sigma menor; densidade baixa => sigma maior)
        point_xy = [(float(p.latitude), float(p.longitude)) for p in points]
        sigmas = self._compute_adaptive_sigmas(point_xy)

        # 3) Kernel e risco por célula
        icra_by_point = {s.point_id: float(s.icra) for s in snapshots}
        point_ids = [p.id for p in points]
        icras_abs = [icra_by_point[pid] for pid in point_ids]
        icras_rel = self._relative_rank_values(icras_abs)
        cell_values: List[Tuple[float, float, float, float, str, str]] = []
        high_risk_cells = 0

        # Pré-cálculo de “tamanho da célula” em graus (para polígonos)
        res_m = self.cfg.grid_resolution_m

        for (cell_center_lat, cell_center_lon, cell_bounds) in grid:
            risk_abs = self._kernel_risk_at(
                lat=cell_center_lat,
                lon=cell_center_lon,
                point_xy=point_xy,
                point_values=icras_abs,
                point_sigmas=sigmas,
            )
            risk_rel = self._kernel_risk_at(
                lat=cell_center_lat,
                lon=cell_center_lon,
                point_xy=point_xy,
                point_values=icras_rel,
                point_sigmas=sigmas,
            )

            level_abs = self._risk_level_from_icra(risk_abs)
            level_rel = self._risk_level_from_icra(risk_rel)

            if risk_abs >= self.cfg.high_risk_threshold:
                high_risk_cells += 1

            min_lat, min_lon, max_lat, max_lon = cell_bounds
            cell_values.append((min_lat, min_lon, risk_abs, risk_rel, level_abs, level_rel))

        total_cells = len(cell_values)

        # 4) GeoJSON (FeatureCollection de células)
        geojson = self._build_geojson_cells(
            cell_values=cell_values,
            resolution_m=res_m,
        )

        # 5) Estatísticas
        total_area_m2 = float(total_cells) * float(res_m) * float(res_m)
        high_risk_area_m2 = float(high_risk_cells) * float(res_m) * float(res_m)
        high_risk_percentage = ((high_risk_area_m2 / total_area_m2) * 100 if total_area_m2 > 0 else 0.0)

        # 6) Validade
        ttl_seconds = int(settings.RISK.SNAPSHOT_TTL_SECONDS)
        valid_until = snapshot_timestamp + timedelta(seconds=ttl_seconds)

        computed_at = self._utcnow()

        # 7) Persistir model
        # kernel_sigma_m: aqui o sigma é adaptativo; armazenamos um valor representativo (mediana/clamp),
        rep_sigma = int(self._median(sigmas)) if sigmas else int(self.cfg.sigma_min_m)

        return RiskSurface(
            municipality_id=int(municipality.id),
            snapshot_timestamp=snapshot_timestamp,
            geojson=geojson,
            grid_resolution_m=int(res_m),
            kernel_sigma_m=rep_sigma,
            total_cells=total_cells,
            total_area_m2=total_area_m2,
            high_risk_area_m2=high_risk_area_m2,
            high_risk_percentage=float(high_risk_percentage),
            computed_at=computed_at,
            valid_until=valid_until,
            source=source,
        )

    # --------------------------------------------------------
    # GRID (bbox + polígono)
    # --------------------------------------------------------

    def _generate_grid(
        self,
        bbox: Tuple[float, float, float, float],
        geometry: Dict[str, Any],
        resolution_m: int,
        max_cells: int,
    ) -> List[Tuple[float, float, Tuple[float, float, float, float]]]:
        """
        Gera grid de células (centros) dentro do polígono do município.
        Retorna lista de:
            (center_lat, center_lon, (min_lat, min_lon, max_lat, max_lon))
        """
        min_lat, min_lon, max_lat, max_lon = bbox
        if min_lat >= max_lat or min_lon >= max_lon:
            raise RiskSurfaceServiceError("BBox inválida no municipality")

        # Conversão metro->grau (aproximação)
        # lat: ~111_320 m por grau
        # lon: ~111_320*cos(lat) m por grau
        lat0 = (min_lat + max_lat) / 2.0
        step_lat = float(resolution_m) / 111_320.0
        step_lon = float(resolution_m) / (111_320.0 * max(0.1, cos(radians(lat0))))

        cells: List[Tuple[float, float, Tuple[float, float, float, float]]] = []
        contains_fn = self._build_geometry_contains_fn(geometry)

        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                center_lat = lat + step_lat / 2.0
                center_lon = lon + step_lon / 2.0

                if contains_fn(center_lon, center_lat):  # (x=lon, y=lat)
                    cell_bounds = (lat, lon, lat + step_lat, lon + step_lon)
                    cells.append((center_lat, center_lon, cell_bounds))

                    if len(cells) >= max_cells:
                        raise RiskSurfaceServiceError(
                            f"Grid excedeu max_cells={max_cells}. "
                            f"Aumente resolução (ex: 700m) ou aumente max_cells."
                        )

                lon += step_lon
            lat += step_lat

        return cells

    # --------------------------------------------------------
    # SIGMA ADAPTATIVO
    # --------------------------------------------------------

    def _compute_adaptive_sigmas(self, point_xy: List[Tuple[float, float]]) -> List[float]:
        """
        Para cada ponto, sigma_i = clamp(min,max, mean(dist_to_kNN) * sigma_scale)
        """
        k = max(1, int(self.cfg.knn_k))
        out: List[float] = []

        for i, (lat_i, lon_i) in enumerate(point_xy):
            dists: List[float] = []
            for j, (lat_j, lon_j) in enumerate(point_xy):
                if i == j:
                    continue
                dists.append(self._haversine_m(lat_i, lon_i, lat_j, lon_j))

            dists.sort()
            if not dists:
                sigma = float(self.cfg.sigma_max_m)
            else:
                use = dists[: min(k, len(dists))]
                mean_k = sum(use) / float(len(use))
                sigma = mean_k * float(self.cfg.sigma_scale)

            sigma = max(float(self.cfg.sigma_min_m), min(float(self.cfg.sigma_max_m), sigma))
            out.append(float(sigma))

        return out

    # --------------------------------------------------------
    # KERNEL
    # --------------------------------------------------------

    def _kernel_risk_at(
        self,
        lat: float,
        lon: float,
        point_xy: List[Tuple[float, float]],
        point_values: List[float],
        point_sigmas: List[float],
    ) -> float:
        """
        Kernel Gaussiano normalizado (para manter 0..1 coerente):
            risk = sum(icra_i * w_i) / sum(w_i)
        """
        num = 0.0
        den = 0.0

        for (plat, plon), value, sigma in zip(point_xy, point_values, point_sigmas):
            d = self._haversine_m(lat, lon, plat, plon)

            # w = exp(-d^2/(2*sigma^2))
            # Evita underflow/overflow: se d muito maior que sigma, peso ~0.
            if sigma <= 0:
                continue

            z = (d * d) / (2.0 * sigma * sigma)
            if z > 60.0:
                continue

            w = self._exp_neg(z)
            num += value * w
            den += w

        if den <= 0.0:
            return 0.0

        risk = num / den
        # clamp final
        if risk < 0.0:
            return 0.0
        if risk > 1.0:
            return 1.0
        return float(risk)

    # --------------------------------------------------------
    # GEOJSON
    # --------------------------------------------------------

    def _build_geojson_cells(
        self,
        cell_values: List[Tuple[float, float, float, float, str, str]],
        resolution_m: int,
    ) -> Dict[str, Any]:
        """
        Constr?i FeatureCollection de pol?gonos de c?lulas.

        cell_values: (min_lat, min_lon, risk_abs, risk_rel, level_abs, level_rel)
        """
        features: List[Dict[str, Any]] = []

        def _relative_color(rank: float) -> str:
            rank = max(0.0, min(1.0, rank))
            hue = (1.0 - rank) * 120.0
            return f"hsl({hue:.2f}, 75%, 45%)"

        for (min_lat, min_lon, risk_abs, risk_rel, level_abs, level_rel) in cell_values:
            step_lat = float(resolution_m) / 111_320.0
            step_lon = float(resolution_m) / (111_320.0 * max(0.1, cos(radians(min_lat + step_lat / 2.0))))

            max_lat = min_lat + step_lat
            max_lon = min_lon + step_lon

            poly = [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]

            color = _relative_color(float(risk_rel))

            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "risk_value": float(risk_abs),
                        "risk_level": level_abs,
                        "risk_value_relative": float(risk_rel),
                        "risk_level_relative": level_rel,
                        "color": color,
                        "grid_resolution_m": int(resolution_m),
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [poly],
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    # --------------------------------------------------------
    # NÍVEL DE RISCO 
    # --------------------------------------------------------

    def _relative_rank_values(self, values: List[float]) -> List[float]:
        if not values:
            return []

        ordered = sorted(float(v) for v in values)
        total = len(ordered)
        if total <= 1:
            return [0.5 for _ in values]

        ranked: List[float] = []
        for v in values:
            pos = bisect_right(ordered, float(v))
            rank = pos / float(total)
            ranked.append(max(0.0, min(1.0, rank)))

        return ranked

    def _risk_level_from_icra(self, icra: float) -> str:
        """
        Como o nível textual nos snapshots vem da IA, aqui precisamos de um critério determinístico.
        Para ficar alinhado e robusto, usamos thresholds configuráveis.
        """
        if icra < self.cfg.t_baixo:
            return "Baixo"
        if icra < self.cfg.t_moderado:
            return "Moderado"
        if icra < self.cfg.t_alto:
            return "Alto"
        return "Muito Alto"

    # --------------------------------------------------------
    # GEOJSON GEOMETRY EXTRACT + POINT IN POLYGON
    # --------------------------------------------------------

    def _extract_geometry(self, geojson: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aceita:
        - FeatureCollection
        - Feature
        - Geometry (Polygon/MultiPolygon)
        Retorna Geometry dict (Polygon/MultiPolygon).
        """
        if not isinstance(geojson, dict):
            raise RiskSurfaceServiceError("municipality.geojson inválido (não é dict)")

        t = geojson.get("type")

        if t == "FeatureCollection":
            feats = geojson.get("features") or []
            if not feats:
                raise RiskSurfaceServiceError("FeatureCollection vazia em municipality.geojson")
            polygons: List[Any] = []

            for feat in feats:
                if not isinstance(feat, dict):
                    continue
                geom = feat.get("geometry")
                if not isinstance(geom, dict):
                    continue
                gtype = geom.get("type")
                coords = geom.get("coordinates")
                if gtype == "Polygon" and isinstance(coords, list):
                    polygons.append(coords)
                elif gtype == "MultiPolygon" and isinstance(coords, list):
                    polygons.extend(coords)

            if not polygons:
                raise RiskSurfaceServiceError("FeatureCollection sem geometry Polygon/MultiPolygon")

            return {
                "type": "MultiPolygon",
                "coordinates": polygons,
            }

        if t == "Feature":
            geom = geojson.get("geometry")
            if not geom:
                raise RiskSurfaceServiceError("Feature sem geometry")
            return geom

        # geometry direto
        if t in ("Polygon", "MultiPolygon"):
            return geojson

        raise RiskSurfaceServiceError(f"Tipo GeoJSON não suportado: {t}")

    def _bbox_from_geometry(self, geometry: Dict[str, Any]) -> Tuple[float, float, float, float]:
        coords = geometry.get("coordinates")
        if not isinstance(coords, list):
            raise RiskSurfaceServiceError("Geometry sem coordinates válidas")

        lons: List[float] = []
        lats: List[float] = []

        def _walk(value: Any, parity: int = 0) -> int:
            if isinstance(value, list):
                p = parity
                for item in value:
                    p = _walk(item, p)
                return p
            if isinstance(value, (int, float)):
                if parity % 2 == 0:
                    lons.append(float(value))
                else:
                    lats.append(float(value))
                return parity + 1
            return parity

        _walk(coords)

        if not lons or not lats:
            raise RiskSurfaceServiceError("Não foi possível extrair bbox da geometry")

        return (min(lats), min(lons), max(lats), max(lons))

    def _build_geometry_contains_fn(self, geometry: Dict[str, Any]) -> Callable[[float, float], bool]:
        if shapely_shape is not None and ShapelyPoint is not None and shapely_prep is not None:
            try:
                prepared = shapely_prep(shapely_shape(geometry))

                def _contains_shapely(x_lon: float, y_lat: float) -> bool:
                    return bool(prepared.covers(ShapelyPoint(float(x_lon), float(y_lat))))

                return _contains_shapely
            except Exception:
                pass

        def _contains_fallback(x_lon: float, y_lat: float) -> bool:
            return self._point_in_geometry(x_lon, y_lat, geometry)

        return _contains_fallback

    def _point_in_geometry(self, x_lon: float, y_lat: float, geometry: Dict[str, Any]) -> bool:
        """
        Retorna True se ponto (lon,lat) estiver dentro de Polygon ou MultiPolygon.
        Suporta buracos (holes) via regra: dentro do anel externo e fora de qualquer hole.
        """
        gtype = geometry.get("type")
        coords = geometry.get("coordinates")

        if gtype == "Polygon":
            return self._point_in_polygon(x_lon, y_lat, coords)

        if gtype == "MultiPolygon":
            for poly in coords:
                if self._point_in_polygon(x_lon, y_lat, poly):
                    return True
            return False

        return False

    def _point_in_polygon(self, x_lon: float, y_lat: float, polygon_coords: Any) -> bool:
        """
        polygon_coords: [ outer_ring, hole1, hole2, ... ]
        ring: [[lon,lat], [lon,lat], ...]
        """
        if not polygon_coords or not isinstance(polygon_coords, list):
            return False

        outer = polygon_coords[0]
        if not self._point_in_ring(x_lon, y_lat, outer):
            return False

        for hole in polygon_coords[1:]:
            if self._point_in_ring(x_lon, y_lat, hole):
                return False

        return True

    def _point_in_ring(self, x: float, y: float, ring: Any) -> bool:
        """
        Ray casting.
        Considera ring fechado ou não.
        """
        if not ring or not isinstance(ring, list):
            return False

        inside = False
        n = len(ring)

        for i in range(n):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]

            intersects = ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1
            )
            if intersects:
                inside = not inside

        return inside

    # --------------------------------------------------------
    # UTILS
    # --------------------------------------------------------

    def _load_config(self) -> SurfaceConfig:
        grid_resolution_m = int(getattr(getattr(settings, "SURFACE", object()), "GRID_RESOLUTION_M", 500))

        knn_k = int(getattr(getattr(settings, "SURFACE", object()), "KNN_K", 5))
        sigma_min_m = int(getattr(getattr(settings, "SURFACE", object()), "SIGMA_MIN_M", 300))
        sigma_max_m = int(getattr(getattr(settings, "SURFACE", object()), "SIGMA_MAX_M", 2500))
        sigma_scale = float(getattr(getattr(settings, "SURFACE", object()), "SIGMA_SCALE", 0.75))

        high_risk_threshold = float(getattr(getattr(settings, "SURFACE", object()), "HIGH_RISK_THRESHOLD", 0.7))

        t_baixo = float(getattr(getattr(settings, "SURFACE", object()), "T_BAIXO", 0.25))
        t_moderado = float(getattr(getattr(settings, "SURFACE", object()), "T_MODERADO", 0.50))
        t_alto = float(getattr(getattr(settings, "SURFACE", object()), "T_ALTO", 0.75))

        max_cells = int(getattr(getattr(settings, "SURFACE", object()), "MAX_CELLS", 200_000))

        if grid_resolution_m <= 0:
            raise RiskSurfaceServiceError("GRID_RESOLUTION_M inválido")
        if not (0.0 < high_risk_threshold <= 1.0):
            raise RiskSurfaceServiceError("HIGH_RISK_THRESHOLD inválido")
        if sigma_min_m <= 0 or sigma_max_m <= 0 or sigma_min_m > sigma_max_m:
            raise RiskSurfaceServiceError("SIGMA_MIN_M/SIGMA_MAX_M inválidos")
        if max_cells <= 0:
            raise RiskSurfaceServiceError("MAX_CELLS inválido")

        return SurfaceConfig(
            grid_resolution_m=grid_resolution_m,
            knn_k=knn_k,
            sigma_min_m=sigma_min_m,
            sigma_max_m=sigma_max_m,
            sigma_scale=sigma_scale,
            high_risk_threshold=high_risk_threshold,
            t_baixo=t_baixo,
            t_moderado=t_moderado,
            t_alto=t_alto,
            max_cells=max_cells,
        )

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    def _haversine_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Distância haversine em metros.
        """
        R = 6371000.0  # raio da Terra em metros
        phi1 = radians(lat1)
        phi2 = radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)

        a = sin(dphi / 2.0) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2.0) ** 2
        c = 2.0 * asin(min(1.0, sqrt(a)))
        return R * c

    def _exp_neg(self, z: float) -> float:
        """
        exp(-z) sem importar math.exp explicitamente aqui,
        usando aproximação estável via pow de e (mantendo simples).
        """
        # e ≈ 2.718281828
        return 2.718281828 ** (-z)

    def _median(self, values: List[float]) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        n = len(s)
        mid = n // 2
        if n % 2 == 1:
            return float(s[mid])
        return float((s[mid - 1] + s[mid]) / 2.0)
