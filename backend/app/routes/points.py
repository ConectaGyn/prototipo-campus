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
from typing import Optional, Dict, Any

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
from backend.app.repositories.municipality_repository import MunicipalityRepository
from backend.app.repositories.risk_surface_repository import RiskSurfaceRepository
from backend.app.services.risk_surface_service import RiskSurfaceService
from backend.app.models.point import Point


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
# ADMIN: ATIVAR TODOS OS PONTOS
# =====================================================

@router.post(
    "/activate-all",
    summary="Ativa todos os pontos críticos",
)
def activate_all_points(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Endpoint administrativo:
    - Marca todos os pontos como ativos
    - Mantém os demais campos inalterados
    """
    try:
        total_points = db.query(Point.id).count()
        inactive_query = db.query(Point).filter(Point.active.is_(False))
        inactive_before = inactive_query.count()

        if inactive_before > 0:
            inactive_query.update({Point.active: True}, synchronize_session=False)
            db.commit()

        active_after = db.query(Point.id).filter(Point.active.is_(True)).count()

        return {
            "message": "Ativacao em lote concluida.",
            "total_points": int(total_points),
            "inactive_before": int(inactive_before),
            "activated": int(inactive_before),
            "active_after": int(active_after),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ativar pontos: {e}",
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
        allowed_sources = {"auto", "cache_only", "compute_only"}
        if source not in allowed_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"source inválido. Use um de: {', '.join(sorted(allowed_sources))}",
            )

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

            if not settings.RISK.FALLBACK_ON_DEMAND:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)

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


# =====================================================
# RECÁLCULO GLOBAL MANUAL (TODOS OS PONTOS)
# =====================================================

@router.post(
    "/recompute-all",
    summary="Dispara recálculo manual de risco para todos os pontos ativos",
)
def recompute_all_points_now(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executa um ciclo manual imediato (pontual):
    - Recalcula todos os pontos ativos no timestamp atual (UTC)
    - Persiste snapshots no banco
    - Recalcula superfícies dos municípios com pontos ativos

    Observação:
    - Endpoint operacional; em produção deve ser protegido por autenticação/autorização.
    """
    try:
        repo = RiskRepository(db)
        orchestrator = RiskOrchestrator(repository=repo)

        reference_ts = orchestrator.get_reference_ts_now()
        points_result = orchestrator.compute_all_points_for_cycle(
            db=db,
            reference_ts=reference_ts,
            only_active=True,
            skip_if_exists=False,
        )

        mrepo = MunicipalityRepository(db)
        srepo = RiskSurfaceRepository(db)
        surface_service = RiskSurfaceService(
            municipality_repo=mrepo,
            surface_repo=srepo,
            risk_repo=repo,
        )

        surface_ok = 0
        surface_skip_no_points = 0
        surface_errors: list[dict[str, str]] = []

        for municipality in mrepo.list_active():
            has_points = (
                db.query(Point.id)
                .filter(
                    Point.active.is_(True),
                    Point.municipality_id == municipality.id,
                )
                .first()
                is not None
            )
            if not has_points:
                surface_skip_no_points += 1
                continue

            try:
                surface_service.get_or_generate_surface(
                    db=db,
                    municipality_id=municipality.id,
                    snapshot_timestamp=reference_ts,
                    force_recompute=True,
                    source="on_demand",
                )
                surface_ok += 1
            except Exception as e:
                surface_errors.append(
                    {"municipality_id": str(municipality.id), "error": repr(e)}
                )

        return {
            "message": "Recalculo manual concluido.",
            "reference_ts": reference_ts.isoformat(),
            "points": points_result,
            "surfaces": {
                "ok": surface_ok,
                "skip_no_points": surface_skip_no_points,
                "failed_count": len(surface_errors),
                "failed": surface_errors[:10],
            },
        }

    except RiskOrchestrationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao recalcular risco global: {e}",
        )
