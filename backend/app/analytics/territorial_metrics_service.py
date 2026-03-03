"""
backend/app/analytics/territorial_metrics_service.py

Serviço de Inteligência Territorial (Analytics) do ClimaGyn.

Responsabilidade:
- Orquestrar leitura de Municipality + RiskSurface (já calculada/persistida)
- Agregar superfície dentro do polígono municipal (via SpatialOps)
- Calcular métricas estratégicas (via MetricsCore)
- Retornar envelope compatível com Schemas (schemas/territorial_metrics.py)
- Compatível com rotas (routes/analytics.py)

Este serviço:
- NÃO recalcula kernel / superfície
- NÃO chama IA
- NÃO chama APIs externas
- NÃO faz escrita no banco (somente leitura)
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.settings import settings
from backend.app.analytics.metrics_core import (
    TerritorialMetricsCalculator,
    TerritorialThresholds,
    CompositeMode,
)
from backend.app.analytics.spatial_ops import (
    aggregate_surface_against_municipality,
)

from backend.app.repositories.municipality_repository import MunicipalityRepository
from backend.app.repositories.risk_surface_repository import RiskSurfaceRepository


# ============================================================
# EXCEÇÕES
# ============================================================

class TerritorialMetricsError(RuntimeError):
    """Erro ao calcular/obter métricas territoriais."""


class MunicipalityNotFound(TerritorialMetricsError):
    """Município não encontrado ou inativo."""


class SurfaceNotFound(TerritorialMetricsError):
    """Superfície não encontrada para o município/timestamp."""


# ============================================================
# SERVICE
# ============================================================

class TerritorialMetricsService:
    """
    Serviço de métricas territoriais.

    Contratos atendidos:
    - routes/analytics.py:
        - get_current_metrics(municipality_id, high_risk_threshold)
        - get_metrics_series(municipality_id, limit, from_ts, to_ts, high_risk_threshold)

    - schemas/territorial_metrics.py:
        TerritorialMetricsResponseSchema:
            municipality
            surface
            high_risk_threshold
            surface_summary
            territorial_metrics

        TerritorialMetricsSeriesResponseSchema:
            municipality
            total
            high_risk_threshold
            series[]:
                snapshot_timestamp
                surface_summary
                territorial_metrics
    """

    def __init__(
        self,
        db: Session,
        *,
        high_risk_threshold: Optional[float] = None,
    ) -> None:
        self.db = db
        self.municipalities = MunicipalityRepository(db)
        self.surfaces = RiskSurfaceRepository(db)

        default_thr = float(getattr(settings.RISK, "HIGH_RISK_THRESHOLD", 0.70))
        self.high_risk_threshold = float(high_risk_threshold) if high_risk_threshold is not None else default_thr

        if not (0.0 <= self.high_risk_threshold <= 1.0):
            raise ValueError("high_risk_threshold deve estar entre 0 e 1.")

    # --------------------------------------------------------
    # MÉTODOS ESPERADOS PELAS ROTAS (routes/analytics.py)
    # --------------------------------------------------------

    def get_current_metrics(
        self,
        municipality_id: int,
        *,
        high_risk_threshold: Optional[float] = None,
        require_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Endpoint-alvo:
            GET /analytics/municipalities/{municipality_id}/metrics
        """
        if high_risk_threshold is not None:
            self._set_threshold(high_risk_threshold)

        municipality = self._load_municipality_or_raise(municipality_id, require_active=require_active)

        surface = self.surfaces.get_latest_by_municipality(municipality_id=municipality.id)

        if not surface:
            raise SurfaceNotFound(f"Nenhuma superfície válida encontrada para municipality_id={municipality.id}")

        return self._build_metrics_envelope(municipality, surface)

    def get_metrics_series(
        self,
        municipality_id: int,
        *,
        limit: int = 30,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        high_risk_threshold: Optional[float] = None,
        require_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Endpoint-alvo:
            GET /analytics/municipalities/{municipality_id}/metrics/series
        """
        if high_risk_threshold is not None:
            self._set_threshold(high_risk_threshold)

        municipality = self._load_municipality_or_raise(municipality_id, require_active=require_active)
        surfaces_desc = self.surfaces.list_by_municipality(municipality_id=municipality.id, limit=None)

        # filtra janela temporal
        filtered: List[Any] = []
        for s in surfaces_desc:
            ts = s.snapshot_timestamp
            if from_ts and ts < from_ts:
                continue
            if to_ts and ts > to_ts:
                continue
            filtered.append(s)

        filtered.sort(key=lambda x: x.snapshot_timestamp)

        if limit is not None and limit > 0:
            filtered = filtered[-limit:]

        series_items: List[Dict[str, Any]] = []
        for s in filtered:
            envelope = self._build_metrics_envelope(municipality, s)
            series_items.append(
                {
                    "snapshot_timestamp": s.snapshot_timestamp,
                    "surface_summary": envelope["surface_summary"],
                    "territorial_metrics": envelope["territorial_metrics"],
                }
            )
        
        return {
            "municipality": self._municipality_payload(municipality),
            "total": len(series_items),
            "high_risk_threshold": self.high_risk_threshold,
            "series": series_items,
        }

    # --------------------------------------------------------
    # HELPERS: THRESHOLD
    # --------------------------------------------------------

    def _set_threshold(self, thr: float) -> None:
        if not (0.0 <= float(thr) <= 1.0):
            raise ValueError("high_risk_threshold deve estar entre 0 e 1.")
        self.high_risk_threshold = float(thr)

    # --------------------------------------------------------
    # CORE 
    # --------------------------------------------------------

    def _build_metrics_envelope(self, municipality: Any, surface: Any) -> Dict[str, Any]:
        """
        Constrói envelope final compatível com:
        - TerritorialMetricsResponseSchema
        """
        aggregated = aggregate_surface_against_municipality(
            municipality_id=municipality.id,
            municipality_geojson=municipality.geojson,
            surface_geojson=surface.geojson,
            snapshot_timestamp_iso=surface.snapshot_timestamp.isoformat(),
            threshold_high_risk=self.high_risk_threshold,
        )

        calculator = TerritorialMetricsCalculator(
            thresholds=TerritorialThresholds(high_risk_threshold=self.high_risk_threshold),
            composite_mode=CompositeMode.RISK_AVERSE,
        )
        core_metrics = calculator.compute(
            aggregated  
        )

        summary = self._build_surface_summary(
            icra_values=aggregated.icra_values,
            total_area_m2=aggregated.total_area_m2,
            high_risk_area_m2=aggregated.high_risk_area_m2,
            total_cells=aggregated.used_cells,
            high_risk_cells=aggregated.high_risk_cells,
        )

        terr = self._map_core_to_schema_metrics(core_metrics, std_icra=summary["std_icra"])

        return {
            "municipality": self._municipality_payload(municipality),
            "surface": self._surface_payload(surface),
            "high_risk_threshold": self.high_risk_threshold,
            "surface_summary": summary,
            "territorial_metrics": terr,
        }

    def _build_surface_summary(
        self,
        *,
        icra_values: List[float],
        total_area_m2: float,
        high_risk_area_m2: float,
        total_cells: int,
        high_risk_cells: int,
    ) -> Dict[str, Any]:
        vals = [float(x) for x in (icra_values or [])]
        vals = [0.0 if x < 0 else 1.0 if x > 1 else x for x in vals]

        total_area_m2 = float(total_area_m2 or 0.0)
        high_risk_area_m2 = float(high_risk_area_m2 or 0.0)
        total_cells = int(total_cells or 0)
        high_risk_cells = int(high_risk_cells or 0)

        high_pct = (high_risk_area_m2 / total_area_m2) if total_area_m2 > 0 else 0.0
        high_pct = 0.0 if high_pct < 0 else 1.0 if high_pct > 1 else float(high_pct)

        mean_icra = float(mean(vals)) if vals else 0.0
        median_icra = float(self._median(vals)) if vals else 0.0
        max_icra = float(max(vals)) if vals else 0.0
        std_icra = float(self._pstdev(vals)) if len(vals) >= 2 else 0.0

        mean_icra = self._clamp01(mean_icra)
        median_icra = self._clamp01(median_icra)
        max_icra = self._clamp01(max_icra)
        std_icra = max(0.0, std_icra)

        return {
            "total_area_m2": total_area_m2,
            "high_risk_area_m2": high_risk_area_m2,
            "high_risk_percentage": high_pct,
            "mean_icra": mean_icra,
            "median_icra": median_icra,
            "max_icra": max_icra,
            "std_icra": std_icra,
            "total_cells": total_cells,
            "high_risk_cells": high_risk_cells,
        }

    def _map_core_to_schema_metrics(self, core_metrics: Any, *, std_icra: float) -> Dict[str, Any]:
        """
        Schema TerritorialMetricsSchema exige:
            severity_score (0..1)
            criticality_score (0..1)
            dispersion_index (>=0)
            exposure_index (0..1)
            risk_classification (Baixo, Moderado, Alto, Crítico)

        Core avançado fornece:
            exposure_index
            mean_intensity
            concentration_index
            composite_index
            classification ("Estável", "Atenção", "Crítico")                       
        """
        exposure = self._clamp01(float(getattr(core_metrics, "exposure_index", 0.0) or 0.0))
        severity = self._clamp01(float(getattr(core_metrics, "mean_intensity", 0.0) or 0.0))
        criticality = self._clamp01(float(getattr(core_metrics, "composite_index", 0.0) or 0.0))

        if criticality <= 0.30:
            cls = "Baixo"
        elif criticality <= 0.50:
            cls = "Moderado"
        elif criticality <= 0.70:
            cls = "Alto"
        else:
            cls = "Crítico"

        return {
            "severity_score": severity,
            "criticality_score": criticality,
            "dispersion_index": float(max(0.0, std_icra)),
            "exposure_index": exposure,
            "risk_classification": cls,
        }

    # --------------------------------------------------------
    # LOADERS / VALIDATIONS
    # --------------------------------------------------------

    def _load_municipality_or_raise(self, municipality_id: int, *, require_active: bool) -> Any:
        municipality = self.municipalities.get_by_id(municipality_id)
        if not municipality:
            raise MunicipalityNotFound(f"Município não encontrado: id={municipality_id}")

        if require_active and not bool(municipality.active):
            raise MunicipalityNotFound(f"Município inativo: id={municipality_id}")

        if not municipality.geojson or not isinstance(municipality.geojson, dict):
            raise TerritorialMetricsError(f"Município id={municipality_id} sem geojson válido no banco.")

        return municipality

    # --------------------------------------------------------
    # PAYLOAD HELPERS 
    # --------------------------------------------------------

    @staticmethod
    def _municipality_payload(m: Any) -> Dict[str, Any]:
        return {
            "id": int(m.id),
            "name": str(m.name),
            "ibge_code": getattr(m, "ibge_code", None),
            "active": bool(getattr(m, "active", True)),
            "bbox_min_lat": float(getattr(m, "bbox_min_lat")),
            "bbox_min_lon": float(getattr(m, "bbox_min_lon")),
            "bbox_max_lat": float(getattr(m, "bbox_max_lat")),
            "bbox_max_lon": float(getattr(m, "bbox_max_lon")),
            "updated_at": getattr(m, "updated_at"),
        }

    @staticmethod
    def _surface_payload(s: Any) -> Dict[str, Any]:
        raw_high_pct = getattr(s, "high_risk_percentage", None)
        high_pct = float(raw_high_pct) if raw_high_pct is not None else None
        if high_pct is not None and high_pct > 1.0 and high_pct <= 100.0:
            high_pct = high_pct / 100.0

        return {
            "snapshot_timestamp": getattr(s, "snapshot_timestamp"),
            "valid_until": getattr(s, "valid_until"),
            "grid_resolution_m": int(getattr(s, "grid_resolution_m")),
            "kernel_sigma_m": int(getattr(s, "kernel_sigma_m")),
            "total_cells": int(getattr(s, "total_cells")) if getattr(s, "total_cells", None) is not None else None,
            "total_area_m2": float(getattr(s, "total_area_m2")) if getattr(s, "total_area_m2", None) is not None else None,
            "high_risk_area_m2": float(getattr(s, "high_risk_area_m2")) if getattr(s, "high_risk_area_m2", None) is not None else None,
            "high_risk_percentage": high_pct,
            "source": str(getattr(s, "source") or "unknown"),
        }

    # --------------------------------------------------------
    # UTILS NUMÉRICOS
    # --------------------------------------------------------

    @staticmethod
    def _clamp01(x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return float(x)

    @staticmethod
    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        n = len(s)
        mid = n // 2
        if n % 2 == 1:
            return float(s[mid])
        return float((s[mid - 1] + s[mid]) / 2.0)

    @staticmethod
    def _pstdev(values: List[float]) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        mu = sum(values) / n
        var = sum((x - mu) ** 2 for x in values) / n
        return var ** 0.5
