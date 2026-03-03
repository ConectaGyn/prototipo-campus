"""
routes/municipalities.py

Camada de exposição da entidade Municipality.

Responsabilidades:
- Gestão estrutural de municípios monitorados
- Exposição de GeoJSON oficial
- Soft delete seguro
- Proteção de endpoints administrativos

Não contém lógica de risco.
"""

from __future__ import annotations

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.repositories.municipality_repository import MunicipalityRepository
from backend.app.models.municipality import Municipality
from backend.app.schemas.municipality import MunicipalityCreateSchema, MunicipalityUpdateSchema, MunicipalityResponseSchema


# ============================================================
# Router
# ============================================================

router = APIRouter(
    prefix="/municipalities",
    tags=["Municipalities"],
)


# ============================================================
# Auth Placeholder 
# ============================================================

def get_current_admin_user():
    """
    Placeholder para futura autenticação.
    Substituir por dependência real de segurança.
    """
    return True

# ============================================================
# Helpers
# ============================================================

def _extract_bbox_from_geojson(geojson: Dict[str, Any]) -> Dict[str, float]:
    """
    Extrai bounding box mínimo de Polygon/MultiPolygon.
    Implementação robusta mas leve.
    """

    def extract_coords(obj):
        if isinstance(obj, list):
            for item in obj:
                yield from extract_coords(item)
        elif isinstance(obj, (int, float)):
            yield obj

    if geojson["type"] == "Feature":
        geometry = geojson.get("geometry", {})
    elif geojson["type"] == "FeatureCollection":
        features = geojson.get("features", [])
        if not features:
            raise HTTPException(status_code=400, detail="FeatureCollection vazia.")
        geometry = features[0].get("geometry", {})
    else:
        raise HTTPException(status_code=400, detail="Tipo GeoJSON não suportado.")

    coords = list(extract_coords(geometry.get("coordinates", [])))
    if len(coords) < 4:
        raise HTTPException(status_code=400, detail="GeoJSON inválido ou sem coordenadas.")

    lons = coords[0::2]
    lats = coords[1::2]

    return {
        "bbox_min_lon": min(lons),
        "bbox_min_lat": min(lats),
        "bbox_max_lon": max(lons),
        "bbox_max_lat": max(lats),
    }


# ============================================================
# Endpoints Públicos
# ============================================================

@router.get("/", response_model=List[MunicipalityResponseSchema])
def list_municipalities(
    db: Session = Depends(get_db),
):
    repo = MunicipalityRepository(db)
    municipalities = repo.list_all()

    return [MunicipalityResponseSchema.from_model(m) for m in municipalities]

@router.get("/{municipality_id}", response_model=MunicipalityResponseSchema)
def get_municipality(
    municipality_id: int,
    db: Session = Depends(get_db),
):
    repo = MunicipalityRepository(db)
    m = repo.get_by_id(municipality_id)

    if not m:
        raise HTTPException(status_code=404, detail="Município não encontrado.")

    return MunicipalityResponseSchema.from_model(m)

@router.get("/{municipality_id}/geojson")
def get_geojson(
    municipality_id: int,
    db: Session = Depends(get_db),
):
    repo = MunicipalityRepository(db)
    m = repo.get_by_id(municipality_id)

    if not m:
        raise HTTPException(status_code=404, detail="Município não encontrado.")

    return m.geojson


# ============================================================
# Endpoints Administrativos (Protegidos)
# ============================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_municipality(
    payload: MunicipalityCreateSchema,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_admin_user),
):
    name = payload.name.strip()
    geojson = payload.geojson
    ibge_code = payload.ibge_code
    active = payload.active if payload.active is not None else True

    bbox = _extract_bbox_from_geojson(geojson)

    repo = MunicipalityRepository(db)

    municipality_obj = Municipality(
        name=name,
        ibge_code=ibge_code,
        geojson=geojson,
        active=active,
        bbox_min_lon=bbox["bbox_min_lon"],
        bbox_min_lat=bbox["bbox_min_lat"],
        bbox_max_lon=bbox["bbox_max_lon"],
        bbox_max_lat=bbox["bbox_max_lat"],
    )

    created = repo.create(municipality_obj)
    return MunicipalityResponseSchema.from_model(created)

@router.patch("/{municipality_id}")
def update_municipality(
    municipality_id: int,
    payload: MunicipalityUpdateSchema,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_admin_user),
):
    repo = MunicipalityRepository(db)
    m = repo.get_by_id(municipality_id)

    if not m:
        raise HTTPException(status_code=404, detail="Município não encontrado.")


    if payload.name is not None:
        m.name = payload.name.strip()

    if payload.ibge_code is not None:
        m.ibge_code = payload.ibge_code
    
    if payload.active is not None:
        m.active = payload.active

    if payload.geojson is not None:
        geojson = payload.geojson
        bbox = _extract_bbox_from_geojson(geojson)
        m.geojson = geojson
        m.bbox_min_lon = bbox["bbox_min_lon"]
        m.bbox_min_lat = bbox["bbox_min_lat"]
        m.bbox_max_lon = bbox["bbox_max_lon"]
        m.bbox_max_lat = bbox["bbox_max_lat"]

    updated = repo.update(m)
    return {"id": updated.id}


@router.delete("/{municipality_id}")
def soft_delete_municipality(
    municipality_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_admin_user),
):
    repo = MunicipalityRepository(db)
    m = repo.get_by_id(municipality_id)

    if not m:
        raise HTTPException(status_code=404, detail="Município não encontrado.")

    repo.deactivate(m)
    return {"status": "deactivated"}
