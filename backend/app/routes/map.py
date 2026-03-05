"""
routes/map.py

Endpoint responsável por fornecer os pontos críticos
com estado de risco consolidado via snapshot.

Este módulo:
- NÃO calcula risco
- NÃO chama IA
- NÃO consulta API climática
- NÃO constrói features
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.point import Point
from backend.app.models.municipality import Municipality
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.schemas.map import MapPointsResponse, MapPointViewSchema
from backend.app.services.risk_relative import compute_relative_levels_by_point
from backend.app.settings import settings

router = APIRouter(
    prefix="/map",
    tags=["Map"],
)


# =====================================================
# ENDPOINT PRINCIPAL
# =====================================================

@router.get(
    "/points",
    response_model=MapPointsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retorna pontos críticos com snapshot atual de risco",
    description=(
        "Retorna todos os pontos críticos ativos com risco consolidado "
        "a partir do snapshot mais recente (sem recalcular IA)."
    ),
)
def get_map_points(
    with_risk: bool = True,
    only_active: bool = True,
    municipality_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Fluxo:
    1. Busca pontos no banco
    2. Busca snapshot mais recente (bucket global)
    3. Consolida resposta
    4. Retorna payload leve
    """

    try:
        # -------------------------------------------------
        # Buscar pontos
        # -------------------------------------------------
        if municipality_id is not None:
            exists = (
                db.query(Municipality.id)
                .filter(
                    Municipality.id == municipality_id,
                    Municipality.active.is_(True),
                )
                .first()
            )
            if not exists:
                raise HTTPException(
                    status_code=404,
                    detail="município não encontrado ou inativo"
                )
            
        query = db.query(Point)    

        if only_active:
            query = query.filter(Point.active.is_(True))

        if municipality_id is not None:
            query = query.filter(Point.municipality_id == municipality_id)

        query = query.order_by(Point.id.asc())
        if municipality_id is None:
            query = query.limit(settings.MAP.MAX_POINTS)
        points: List[Point] = query.all()

        # -------------------------------------------------
        # Buscar snapshot mais recente global
        # -------------------------------------------------

        repository = RiskRepository(db)

        point_ids = [p.id for p in points]
        snapshot_timestamp: Optional[datetime] = None

        snapshots_by_point: Dict[str, object] = {}
        relative_level_by_point: Dict[str, str] = {}

        if with_risk and point_ids:
            snapshot_timestamp = repository.get_latest_complete_bucket_timestamp(point_ids)
            if snapshot_timestamp is None:
                snapshot_timestamp = repository.get_latest_bucket_timestamp_for_points(point_ids)

        if with_risk and snapshot_timestamp:
            snapshots = repository.get_snapshots_by_bucket(
                snapshot_timestamp=snapshot_timestamp
            )

            snapshots_by_point = {
                s.point_id: s for s in snapshots
            }
            relative_level_by_point = compute_relative_levels_by_point(snapshots)

        # -------------------------------------------------
        # Montar resposta
        # -------------------------------------------------

        response_points: List[MapPointViewSchema] = []

        for p in points:
            snapshot = snapshots_by_point.get(p.id)

            response_points.append(
                MapPointViewSchema(
                    id=p.id,
                    nome=p.name,
                    latitude=p.latitude,
                    longitude=p.longitude,
                    bairro=p.neighborhood,
                    raio_influencia_m=p.influence_radius_m,
                    ativo=p.active,
                    municipality_id=p.municipality_id,
                    icra=snapshot.icra if snapshot else None,
                    icra_std=snapshot.icra_std if snapshot else None,
                    nivel_risco=snapshot.nivel_risco if snapshot else None,
                    nivel_risco_relativo=(
                        relative_level_by_point.get(p.id) if snapshot else None
                    ),
                    confianca=snapshot.confianca if snapshot else None,
                    referencia_em=(
                        snapshot.snapshot_timestamp
                        if snapshot else None
                    ),
                )
            )

        # -------------------------------------------------
        # Metadata snapshot
        # -------------------------------------------------

        snapshot_valid_until: Optional[datetime] = None

        if snapshot_timestamp:
            snapshot_valid_until = (
                snapshot_timestamp +
                timedelta(seconds=settings.RISK.SNAPSHOT_TTL_SECONDS)
            )

        return MapPointsResponse(
            snapshot_timestamp=snapshot_timestamp,
            snapshot_valid_until=snapshot_valid_until,
            total=len(response_points),
            pontos=response_points,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consolidar dados do mapa: {e}",
        )
