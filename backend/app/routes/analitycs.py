"""
routes/analytics.py

Endpoints institucionais de Analytics (Inteligencia Territorial).

Este modulo:
- Nao calcula risco
- Nao recalcula superficie
- Nao acessa IA/clima
- Apenas valida entrada e orquestra chamadas ao TerritorialMetricsService
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.settings import settings

from backend.app.analytics.territorial_metrics_service import (
    TerritorialMetricsService,
    TerritorialMetricsError,
    MunicipalityNotFound,
    SurfaceNotFound,
)

from backend.app.schemas.territorial_metrics import (
    TerritorialMetricsResponseSchema,
    TerritorialMetricsSeriesResponseSchema,
)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


# =====================================================
# HELPERS
# =====================================================

def _parse_iso_dt(value: Optional[str], field_name: str) -> Optional[datetime]:
    """
    Parse robusto de datetime ISO 8601.
    - Aceita timezone-aware ("...-03:00", "...Z")
    - Se vier naive (sem tzinfo), assume UTC para evitar comparacoes inconsistentes.
    """
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parametro '{field_name}' deve ser datetime ISO 8601 valido.",
        )


def _validate_limit(limit: int) -> int:
    """
    Limites institucionais (evita queries pesadas no banco).
    """
    hard_max = int(getattr(getattr(settings, "ANALYTICS", object()), "MAX_SERIES_LIMIT", 200) or 200)

    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parametro 'limit' deve ser > 0.",
        )
    if limit > hard_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parametro 'limit' excede o maximo permitido ({hard_max}).",
        )
    return limit


def _map_domain_error_to_http(e: TerritorialMetricsError) -> HTTPException:
    """
    Traducao explicita de erros de dominio para HTTP.
    Mantem robustez e evita "tudo vira 404" sem criterio.
    """
    if isinstance(e, (MunicipalityNotFound, SurfaceNotFound)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# =====================================================
# ENDPOINTS
# =====================================================

@router.get(
    "/municipalities/{municipality_id}/metrics",
    response_model=TerritorialMetricsResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Metricas territoriais atuais do municipio (snapshot mais recente disponivel)",
    description=(
        "Retorna metricas territoriais consolidadas a partir da superficie de risco "
        "mais recente disponivel para o municipio. Nao recalcula superficie."
    ),
)
def get_municipality_metrics(
    municipality_id: int,
    high_risk_threshold: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "Threshold opcional para classificar 'alto risco' (ICRA >= threshold). "
            "Se omitido, usa configuracao padrao do backend."
        ),
    ),
    threshold_high: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Parametro legado (use high_risk_threshold).",
    ),
    db: Session = Depends(get_db),
):
    """
    Retorna metricas territoriais do snapshot mais recente disponivel do municipio.

    Observacao:
    - Caso nao exista superficie registrada, retorna 404.
    """
    service = TerritorialMetricsService(db=db)
    threshold = (
        high_risk_threshold if high_risk_threshold is not None else threshold_high
    )

    try:
        return service.get_current_metrics(
            municipality_id=municipality_id,
            high_risk_threshold=threshold,
        )
    except TerritorialMetricsError as e:
        raise _map_domain_error_to_http(e)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter metricas territoriais: {e}",
        )


@router.get(
    "/municipalities/{municipality_id}/metrics/series",
    response_model=TerritorialMetricsSeriesResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Serie historica de metricas territoriais do municipio",
    description=(
        "Retorna uma serie temporal (lista) de metricas territoriais consolidadas "
        "por snapshot da superficie de risco. Nao recalcula superficie."
    ),
)
def get_municipality_metrics_series(
    municipality_id: int,
    limit: int = Query(
        30,
        description="Quantidade maxima de snapshots retornados (ordem cronologica crescente).",
    ),
    from_ts: Optional[str] = Query(
        None,
        description="Datetime ISO 8601 (inclusivo) para filtrar a partir deste timestamp.",
    ),
    to_ts: Optional[str] = Query(
        None,
        description="Datetime ISO 8601 (inclusivo) para filtrar ate este timestamp.",
    ),
    high_risk_threshold: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "Threshold opcional para classificar 'alto risco' (ICRA >= threshold). "
            "Se omitido, usa configuracao padrao do backend."
        ),
    ),
    threshold_high: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Parametro legado (use high_risk_threshold).",
    ),
    db: Session = Depends(get_db),
):
    """
    Serie historica de metricas:

    - Ordenacao: crescente (mais antigo -> mais recente)
    - Se from_ts/to_ts forem informados, aplica janela temporal.
    - Se limit for informado, aplica limite apos filtros (server-side).
    """
    parsed_from = _parse_iso_dt(from_ts, "from_ts")
    parsed_to = _parse_iso_dt(to_ts, "to_ts")
    limit = _validate_limit(limit)

    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parametros invalidos: 'from_ts' nao pode ser maior que 'to_ts'.",
        )

    service = TerritorialMetricsService(db=db)
    threshold = (
        high_risk_threshold if high_risk_threshold is not None else threshold_high
    )

    try:
        return service.get_metrics_series(
            municipality_id=municipality_id,
            limit=limit,
            from_ts=parsed_from,
            to_ts=parsed_to,
            high_risk_threshold=threshold,
        )
    except TerritorialMetricsError as e:
        raise _map_domain_error_to_http(e)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter serie historica de metricas: {e}",
        )
