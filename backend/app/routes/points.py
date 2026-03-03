"""
routes/points.py

Rotas relacionadas aos pontos críticos e seus estados de risco.

Este módulo:
- NÃO calcula risco diretamente
- NÃO acessa APIs externas
- NÃO implementa regra de negócio complexa
- Apenas orquestra chamadas ao RiskOrchestrator
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.settings import settings
from backend.app.services.risk_orchestrator import (
    RiskOrchestrator,
    RiskOrchestrationError,
)
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.schemas.point import PointResponse
from backend.app.schemas.map import RiskSnapshotResponse
from backend.app.services.risk_relative import compute_relative_levels_by_point


router = APIRouter(prefix="/points", tags=["Points"])


# =====================================================
# LISTAGEM DE PONTOS (METADADOS)
# =====================================================

@router.get(
    "",
    response_model=list[PointResponse],
    summary="Lista todos os pontos críticos monitorados",
)
def list_points(
    db: Session = Depends(get_db),
):
    """
    Retorna apenas metadados dos pontos (sem risco).
    """

    try:
        repo = RiskRepository(db)
        orchestrator = RiskOrchestrator(repository=repo)

        points = orchestrator.list_points(db=db, only_active=False)

        return [PointResponse.model_validate(p) for p in points]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar pontos: {e}",
        )


# =====================================================
# RISCO POR PONTO (SNAPSHOT GLOBAL)
# =====================================================

@router.get(
    "/{point_id}/risk",
    response_model=RiskSnapshotResponse,
    summary="Retorna risco do ponto com snapshot intervalado",
)
def get_point_risk(
    point_id: str,
    at: Optional[datetime] = Query(
        None,
        description="Timestamp ISO para consultar bucket específico",
    ),
    refresh: bool = Query(
        False,
        description="Força recálculo do snapshot",
    ),
    source: str = Query(
        "auto",
        description="auto | cache_only | compute_only",
    ),
    db: Session = Depends(get_db),
):

    try:
        repo = RiskRepository(db)
        orchestrator = RiskOrchestrator(repository=repo)

        # -------------------------------------------------
        # Define bucket global
        # -------------------------------------------------

        reference_ts = at or orchestrator.get_reference_ts_now()

        # -------------------------------------------------
        # CACHE ONLY
        # -------------------------------------------------

        if source == "cache_only":
            snapshot = repo.get_snapshot(
                point_id=point_id,
                snapshot_timestamp=reference_ts,
            )

            if not snapshot:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)

            bucket_snaps = repo.get_snapshots_by_bucket(reference_ts)
            relative = compute_relative_levels_by_point(bucket_snaps).get(point_id)
            return RiskSnapshotResponse.from_model(
                snapshot,
                source="snapshot",
                relative_level=relative,
            )

        # -------------------------------------------------
        # AUTO MODE (padrão)
        # -------------------------------------------------

        if not refresh and source != "compute_only":
            snapshot = repo.get_snapshot(
                point_id=point_id,
                snapshot_timestamp=reference_ts,
            )

            if snapshot:
                bucket_snaps = repo.get_snapshots_by_bucket(reference_ts)
                relative = compute_relative_levels_by_point(bucket_snaps).get(point_id)
                return RiskSnapshotResponse.from_model(
                    snapshot,
                    source="snapshot",
                    relative_level=relative,
                )

        # -------------------------------------------------
        # COMPUTE / FALLBACK
        # -------------------------------------------------

        snapshot = orchestrator.get_or_compute_point_snapshot(
            db=db,
            point_id=point_id,
            reference_ts=reference_ts,
            force_recompute=refresh or source == "compute_only",
        )

        bucket_snaps = repo.get_snapshots_by_bucket(reference_ts)
        relative = compute_relative_levels_by_point(bucket_snaps).get(point_id)
        return RiskSnapshotResponse.from_model(
            snapshot,
            source="on_demand",
            relative_level=relative,
        )

    except RiskOrchestrationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado ao obter risco: {e}",
        )