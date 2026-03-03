"""
routes/surface.py

Rotas responsáveis por servir a superfície espacial de risco
(baseada em kernel) para municípios.

Responsabilidades:
- Expor superfície GeoJSON para frontend
- Garantir cache via banco (JSONB)
- Delegar decisão de cálculo ao RiskSurfaceService
- Não conter lógica de negócio pesada
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.municipality import Municipality
from backend.app.repositories.municipality_repository import MunicipalityRepository
from backend.app.repositories.risk_surface_repository import RiskSurfaceRepository
from backend.app.services.risk_surface_service import RiskSurfaceService
from backend.app.repositories.risk_repository import RiskRepository


# ============================================================
# Router
# ============================================================

router = APIRouter(
    prefix="/surface",
    tags=["Surface"],
)


# ============================================================
# Helpers
# ============================================================

def _get_active_municipality_or_404(
    db: Session,
    municipality_id: int,
) -> Municipality:
    repo = MunicipalityRepository(db)
    municipality = repo.get_by_id(municipality_id)

    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Município não encontrado.",
        )

    if not municipality.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Município inativo.",
        )

    return municipality


# ============================================================
# GET /surface/{municipality_id}
# ============================================================

@router.get("/{municipality_id}")
def get_surface(
    municipality_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retorna envelope completo da superfície espacial do município.

    Comportamento:
    - Busca superfície válida no banco
    - Se expirou ou não existir → recalcula automaticamente
    - Retorna GeoJSON + metadados + estatísticas
    """

    municipality = _get_active_municipality_or_404(db, municipality_id)

    surface_repo = RiskSurfaceRepository(db)
    risk_repo = RiskRepository(db)

    snapshot_ts = risk_repo.get_latest_bucket_timestamp()

    if not snapshot_ts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum snapshot de risco disponível no sistema."
        )
    
    service = RiskSurfaceService(
        municipality_repo=MunicipalityRepository(db),
        surface_repo=surface_repo,
        risk_repo=risk_repo,
    )

    try:
        surface = service.get_or_generate_surface(
            db=db,
            municipality_id=municipality.id,
            snapshot_timestamp=snapshot_ts,
            force_recompute=False,
            source="on_demand",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar superfície: {repr(e)}",
        )

    return {
        "municipality_id": municipality.id,
        "municipality_name": municipality.name,
        "reference_ts": surface.snapshot_timestamp.isoformat(),
        "computed_at": surface.computed_at.isoformat(),
        "valid_until": surface.valid_until.isoformat() if surface.valid_until else None,
        "grid_resolution_m": surface.grid_resolution_m,
        "kernel_sigma_m": surface.kernel_sigma_m,
        "stats": {
            "total_cells": surface.total_cells,
            "total_area_m2": surface.total_area_m2,
            "high_risk_area_m2": surface.high_risk_area_m2,
            "high_risk_percentage": surface.high_risk_percentage,
        },
        "geojson": surface.geojson,
    }


# ============================================================
# GET /surface/{municipality_id}/metadata
# ============================================================

@router.get("/{municipality_id}/metadata")
def get_surface_metadata(
    municipality_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retorna apenas metadados e estatísticas da superfície.
    Não retorna o GeoJSON completo.
    """

    municipality = _get_active_municipality_or_404(db, municipality_id)

    surface_repo = RiskSurfaceRepository(db)
    latest_surface = surface_repo.get_latest_by_municipality(
        municipality_id=municipality.id
    )

    if not latest_surface:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Superfície ainda não gerada para este município.",
        )

    return {
        "municipality_id": municipality.id,
        "reference_ts": latest_surface.snapshot_timestamp.isoformat(),
        "computed_at": latest_surface.computed_at.isoformat(),
        "valid_until": latest_surface.valid_until.isoformat() if latest_surface.valid_until else None,
        "grid_resolution_m": latest_surface.grid_resolution_m,
        "kernel_sigma_m": latest_surface.kernel_sigma_m,
        "stats": {
            "total_cells": latest_surface.total_cells,
            "total_area_m2": latest_surface.total_area_m2,
            "high_risk_area_m2": latest_surface.high_risk_area_m2,
            "high_risk_percentage": latest_surface.high_risk_percentage,
        },
    }


# ============================================================
# POST /surface/{municipality_id}/recompute
# ============================================================

@router.post("/{municipality_id}/recompute")
def recompute_surface(
    municipality_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Força recomputação da superfície.

    Deve ser protegido por autenticação administrativa.
    """

    municipality = _get_active_municipality_or_404(db, municipality_id)

    surface_repo = RiskSurfaceRepository(db)
    risk_repo = RiskRepository(db)

    snapshot_ts = risk_repo.get_latest_bucket_timestamp()

    if not snapshot_ts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum snapshot de risco disponível no sistema."
        )

    service = RiskSurfaceService(
        municipality_repo=MunicipalityRepository(db),
        surface_repo=surface_repo,
        risk_repo=risk_repo,
    )

    try:
        surface = service.get_or_generate_surface(
            db=db,
            municipality_id=municipality.id,
            snapshot_timestamp=snapshot_ts,
            force_recompute=True,
            source="on_demand",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao recomputar superfície: {repr(e)}",
        )

    return {
        "message": "Superfície recalculada com sucesso.",
        "municipality_id": municipality.id,
        "reference_ts": surface.snapshot_timestamp.isoformat(),
        "computed_at": surface.computed_at.isoformat(),
    }

