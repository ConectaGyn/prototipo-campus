"""
analytics/spatial_ops.py

Operações espaciais (geometria + área + filtragem) para o módulo de Analytics.

Responsabilidades:
- Validar/normalizar GeoJSON (municipality e surface)
- Converter GeoJSON -> geometrias Shapely
- Projetar geometrias para CRS métrico (UTM dinâmico) para cálculo de área em m²
- Filtrar células cuja geometria (ou centro) esteja dentro do polígono municipal
- Agregar dados espaciais básicos para consumo do metrics_core

Princípios:
- Módulo puro: NÃO acessa banco, NÃO conhece FastAPI, NÃO chama serviços externos
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from shapely.prepared import prep as shapely_prep

try:
    # Shapely 2.x
    from shapely.validation import make_valid  
except Exception:  
    make_valid = None  

from pyproj import CRS, Transformer


# =====================================================
# EXCEÇÕES
# =====================================================

class SpatialOpsError(RuntimeError):
    """Erro geral de operações espaciais."""

class InvalidGeoJSONError(SpatialOpsError):
    """GeoJSON inválido ou inesperado."""

class ProjectionError(SpatialOpsError):
    """Falha ao projetar geometria."""


# =====================================================
# DTOS DE APOIO
# =====================================================

@dataclass(frozen=True)
class SpatialCell:
    """
    Representa uma célula do grid (uma feature do risk_surface.geojson).
    """
    feature_id: str
    geometry_wgs84: BaseGeometry
    centroid_wgs84: ShapelyPoint
    icra: float
    properties: Dict[str, Any]


@dataclass(frozen=True)
class AggregatedSpatialData:
    """
    Agregado mínimo para o núcleo de métricas (metrics_core).
    """
    municipality_id: int
    snapshot_timestamp_iso: str

    total_area_m2: float
    high_risk_area_m2: float

    total_cells: int
    used_cells: int
    high_risk_cells: int

    icra_values: List[float]

    cell_area_m2: Optional[float]
    threshold_high_risk: float
    method: str 

    metadata: Optional[Dict[str, object]] = None


# =====================================================
# HELPERS BÁSICOS
# =====================================================

def _is_mapping(obj: Any) -> bool:
    return isinstance(obj, dict)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return float(default)
        if isinstance(v, bool):
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2.0)


def _try_make_valid(geom: BaseGeometry) -> BaseGeometry:
    """
    Tenta corrigir geometria inválida.
    Preferência:
    - shapely.validation.make_valid (Shapely 2.x)
    - fallback: buffer(0)
    """
    try:
        if make_valid is not None:
            fixed = make_valid(geom)
            if fixed and not fixed.is_empty:
                return fixed
    except Exception:
        pass

    try:
        fixed = geom.buffer(0)
        if fixed and not fixed.is_empty:
            return fixed
    except Exception:
        pass

    return geom


def _extract_surface_meta(surface_geojson: Dict[str, Any]) -> Dict[str, object]:
    """
    Extrai metadados úteis do GeoJSON da superfície sem depender de envelope externo.

    Estratégia:
    - tenta puxar grid_resolution_m da primeira feature.properties
    - tenta inferir kernel_sigma_m se existir em properties
    """
    meta: Dict[str, object] = {}
    try:
        feats = surface_geojson.get("features")
        if isinstance(feats, list) and feats:
            f0 = feats[0]
            if isinstance(f0, dict):
                props = f0.get("properties")
                if isinstance(props, dict):
                    if "grid_resolution_m" in props:
                        meta["grid_resolution_m"] = int(_safe_float(props.get("grid_resolution_m"), 0.0))
                    for k in ("kernel_sigma_m", "sigma_m", "kernel_sigma"):
                        if k in props:
                            meta["kernel_sigma_m"] = int(_safe_float(props.get(k), 0.0))
                            break
    except Exception:
        pass
    return meta


# =====================================================
# VALIDAÇÃO / NORMALIZAÇÃO GEOJSON
# =====================================================

def validate_municipality_geojson(geojson: Dict[str, Any]) -> None:
    """
    Valida se o GeoJSON de município é:
    - Polygon/MultiPolygon (geometry pura)
    - Feature com geometry Polygon/MultiPolygon
    - FeatureCollection contendo Features com geometry Polygon/MultiPolygon
    """
    if not _is_mapping(geojson):
        raise InvalidGeoJSONError("GeoJSON do município deve ser um dict.")

    gtype = geojson.get("type")
    if not gtype:
        raise InvalidGeoJSONError("GeoJSON do município sem campo 'type'.")

    if gtype == "Feature":
        geom = geojson.get("geometry")
        if not _is_mapping(geom):
            raise InvalidGeoJSONError("Feature do município sem 'geometry' válido.")
        gtype = geom.get("type")
        if gtype not in {"Polygon", "MultiPolygon"}:
            raise InvalidGeoJSONError(
                f"GeoJSON do município deve ser Polygon/MultiPolygon. Recebido: {gtype}"
            )
        return

    if gtype == "FeatureCollection":
        features = geojson.get("features")
        if not isinstance(features, list) or not features:
            raise InvalidGeoJSONError("FeatureCollection do município sem 'features' válido.")

        for i, f in enumerate(features[:5]):
            if not _is_mapping(f) or f.get("type") != "Feature":
                raise InvalidGeoJSONError(
                    f"Feature inválida na FeatureCollection do município (index={i})."
                )
            geom = f.get("geometry")
            if not _is_mapping(geom) or geom.get("type") not in {"Polygon", "MultiPolygon"}:
                raise InvalidGeoJSONError(
                    f"Geometria inválida na FeatureCollection do município (index={i}): "
                    f"{geom.get('type') if _is_mapping(geom) else None}"
                )
        return

    if gtype not in {"Polygon", "MultiPolygon"}:
        raise InvalidGeoJSONError(
            f"GeoJSON do município deve ser Polygon/MultiPolygon/Feature/FeatureCollection. Recebido: {gtype}"
        )


def validate_surface_geojson(geojson: Dict[str, Any]) -> None:
    """
    Valida se o GeoJSON da superfície é FeatureCollection com Features Polygon/MultiPolygon.
    """
    if not _is_mapping(geojson):
        raise InvalidGeoJSONError("GeoJSON da superfície deve ser um dict.")

    gtype = geojson.get("type")
    if gtype != "FeatureCollection":
        raise InvalidGeoJSONError(
            f"GeoJSON da superfície deve ser FeatureCollection. Recebido: {gtype}"
        )

    features = geojson.get("features")
    if not isinstance(features, list):
        raise InvalidGeoJSONError("FeatureCollection sem lista 'features'.")

    for i, f in enumerate(features[:5]):
        if not _is_mapping(f) or f.get("type") != "Feature":
            raise InvalidGeoJSONError(f"Feature inválida na superfície (index={i}).")
        geom = f.get("geometry")
        if not _is_mapping(geom) or geom.get("type") not in {"Polygon", "MultiPolygon"}:
            raise InvalidGeoJSONError(
                f"Geometria inválida na superfície (index={i}): {geom.get('type') if _is_mapping(geom) else None}"
            )


# =====================================================
# CONVERSÕES SHAPELY
# =====================================================

def municipality_geojson_to_geometry(geojson: Dict[str, Any]) -> BaseGeometry:
    """
    Converte GeoJSON de município -> Shapely geometry (WGS84).
    """
    validate_municipality_geojson(geojson)

    gtype = geojson.get("type")
    geom: BaseGeometry

    if gtype == "FeatureCollection":
        features = geojson.get("features") or []
        geoms: List[BaseGeometry] = []

        for idx, f in enumerate(features):
            if not _is_mapping(f) or f.get("type") != "Feature":
                raise InvalidGeoJSONError(
                    f"Feature inválida na FeatureCollection do município (index={idx})."
                )

            geom_obj = f.get("geometry")
            if not _is_mapping(geom_obj):
                continue

            try:
                g = shape(geom_obj)
            except Exception:
                continue

            if not g.is_valid:
                g = _try_make_valid(g)

            if not g.is_empty:
                geoms.append(g)

        if not geoms:
            raise InvalidGeoJSONError("FeatureCollection do município sem geometrias válidas.")

        from shapely.ops import unary_union
        geom = unary_union(geoms)

    elif gtype == "Feature":
        geom_obj = geojson.get("geometry")
        if not _is_mapping(geom_obj):
            raise InvalidGeoJSONError("Feature do município sem 'geometry' válido.")
        geom = shape(geom_obj)

    else:
        geom = shape(geojson)

    if not geom.is_valid:
        geom = _try_make_valid(geom)

    if geom.is_empty:
        raise InvalidGeoJSONError("Geometria do município vazia após conversão/validação.")

    return geom


def surface_geojson_to_cells(
    geojson: Dict[str, Any],
    *,
    icra_property: str = "icra",
) -> List[SpatialCell]:
    """
    Converte FeatureCollection -> lista de células.
    """
    validate_surface_geojson(geojson)

    features = geojson["features"]
    out: List[SpatialCell] = []

    fallbacks = [icra_property, "icra", "risk_value", "value"]

    for idx, f in enumerate(features):
        try:
            geom_obj = f.get("geometry")
            if not _is_mapping(geom_obj):
                continue

            geom = shape(geom_obj)
            if not geom.is_valid:
                geom = _try_make_valid(geom)
            if geom.is_empty:
                continue

            props = f.get("properties") if _is_mapping(f.get("properties")) else {}
            fid = str(f.get("id") or props.get("id") or f"cell_{idx}")

            v = None
            for k in fallbacks:
                if props is not None and k in props:
                    v = props.get(k)
                    break

            icra = _safe_float(v, default=0.0)
            if icra < 0.0:
                icra = 0.0
            elif icra > 1.0:
                icra = 1.0

            centroid = geom.centroid
            if centroid.is_empty:
                continue

            out.append(
                SpatialCell(
                    feature_id=fid,
                    geometry_wgs84=geom,
                    centroid_wgs84=ShapelyPoint(float(centroid.x), float(centroid.y)),
                    icra=float(icra),
                    properties=props or {},
                )
            )
        except Exception:
            continue

    return out


# =====================================================
# PROJEÇÃO / ÁREA (UTM dinâmico)
# =====================================================

def detect_utm_crs_for_geometry_wgs84(geom_wgs84: BaseGeometry) -> CRS:
    if geom_wgs84.is_empty:
        raise ProjectionError("Geometria vazia para detecção UTM.")

    c = geom_wgs84.centroid
    lon = float(c.x)
    lat = float(c.y)

    zone = int((lon + 180.0) // 6.0) + 1
    is_south = lat < 0

    epsg = 32700 + zone if is_south else 32600 + zone
    try:
        return CRS.from_epsg(epsg)
    except Exception as e:
        raise ProjectionError(f"Falha ao construir CRS UTM EPSG:{epsg}: {e}") from e


def build_transformer_wgs84_to(crs_target: CRS) -> Transformer:
    try:
        return Transformer.from_crs(
            CRS.from_epsg(4326),
            crs_target,
            always_xy=True,
        )
    except Exception as e:
        raise ProjectionError(f"Falha ao criar Transformer: {e}") from e


def project_geometry(geom_wgs84: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    try:
        return shapely_transform(transformer.transform, geom_wgs84)
    except Exception as e:
        raise ProjectionError(f"Falha ao projetar geometria: {e}") from e


def compute_area_m2_of_geometry(geom_wgs84: BaseGeometry, transformer: Transformer) -> float:
    g = project_geometry(geom_wgs84, transformer)
    area = float(getattr(g, "area", 0.0) or 0.0)
    return 0.0 if area < 0 else area


# =====================================================
# FILTRAGEM ESPACIAL
# =====================================================

def filter_cells_by_centroid_within_polygon(
    cells: List[SpatialCell],
    municipality_geom_wgs84: BaseGeometry,
) -> List[SpatialCell]:
    if municipality_geom_wgs84.is_empty:
        return []

    prepared = shapely_prep(municipality_geom_wgs84)
    out: List[SpatialCell] = []

    for c in cells:
        try:
            if prepared.contains(c.centroid_wgs84):
                out.append(c)
                continue
        except Exception:
            pass

        try:
            if municipality_geom_wgs84.covers(c.centroid_wgs84):
                out.append(c)
        except Exception:
            continue

    return out


# =====================================================
# AGREGAÇÃO PRINCIPAL
# =====================================================

def aggregate_surface_against_municipality(
    *,
    municipality_id: int,
    municipality_geojson: Dict[str, Any],
    surface_geojson: Dict[str, Any],
    snapshot_timestamp_iso: str,
    threshold_high_risk: float = 0.70,
    icra_property: str = "icra",
) -> AggregatedSpatialData:
    thr = float(threshold_high_risk)
    if not (0.0 <= thr <= 1.0):
        raise SpatialOpsError("threshold_high_risk deve estar entre 0 e 1.")

    muni_geom = municipality_geojson_to_geometry(municipality_geojson)
    cells = surface_geojson_to_cells(surface_geojson, icra_property=icra_property)
    inside_cells = filter_cells_by_centroid_within_polygon(cells, muni_geom)

    utm_crs = detect_utm_crs_for_geometry_wgs84(muni_geom)
    transformer = build_transformer_wgs84_to(utm_crs)

    total_area_m2 = compute_area_m2_of_geometry(muni_geom, transformer)

    used_cells = 0
    high_cells = 0
    high_area_m2 = 0.0
    icra_values: List[float] = []
    cell_areas: List[float] = []

    for c in inside_cells:
        used_cells += 1
        icra_values.append(float(c.icra))

        area_cell = compute_area_m2_of_geometry(c.geometry_wgs84, transformer)
        if area_cell > 0:
            cell_areas.append(area_cell)

        if c.icra >= thr:
            high_cells += 1
            high_area_m2 += area_cell

    cell_area_m2 = _median(cell_areas) if cell_areas else None

    meta: Dict[str, object] = {
        "municipality_id": int(municipality_id),
        "snapshot_timestamp": str(snapshot_timestamp_iso),
        "grid_total_cells": int(len(cells)),
        "grid_used_cells": int(used_cells),
        "grid_high_risk_cells": int(high_cells),
        "threshold_high_risk": float(thr),
        "method": "centroid_within_polygon",
    }
    meta.update(_extract_surface_meta(surface_geojson))

    return AggregatedSpatialData(
        municipality_id=int(municipality_id),
        snapshot_timestamp_iso=str(snapshot_timestamp_iso),
        total_area_m2=float(total_area_m2 or 0.0),
        high_risk_area_m2=float(high_area_m2 or 0.0),
        total_cells=int(len(cells)),
        used_cells=int(used_cells),
        high_risk_cells=int(high_cells),
        icra_values=icra_values,
        cell_area_m2=cell_area_m2,
        threshold_high_risk=float(thr),
        method="centroid_within_polygon",
        metadata=meta,  
    )
