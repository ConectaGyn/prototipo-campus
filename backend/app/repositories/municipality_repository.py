"""
repositories/municipality_repository.py

Camada de acesso a dados para a entidade Municipality.

Responsabilidades:
- CRUD de municípios
- Consultas estratégicas para geração de superfície
- Controle de ativação/desativação
- Garantia de integridade

Este arquivo NÃO contém regra de negócio espacial.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.municipality import Municipality


class MunicipalityRepository:
    """
    Repositório responsável por operações de persistência
    da entidade Municipality.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==========================================================
    # CREATE
    # ==========================================================

    def create(self, municipality: Municipality) -> Municipality:
        """
        Persiste um novo município.

        Lança:
            IntegrityError se houver violação de unicidade (ex: nome duplicado).
        """
        try:
            self.db.add(municipality)
            self.db.commit()
            self.db.refresh(municipality)
            return municipality
        except IntegrityError:
            self.db.rollback()
            raise

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(self, municipality: Municipality) -> Municipality:
        """
        Atualiza um município já existente.
        O objeto deve já estar associado à sessão.
        """
        try:
            self.db.commit()
            self.db.refresh(municipality)
            return municipality
        except IntegrityError:
            self.db.rollback()
            raise

    # ==========================================================
    # READ
    # ==========================================================

    def get_by_id(self, municipality_id: int) -> Optional[Municipality]:
        return (
            self.db.query(Municipality)
            .filter(Municipality.id == municipality_id)
            .first()
        )

    def get_by_name(self, name: str) -> Optional[Municipality]:
        return (
            self.db.query(Municipality)
            .filter(Municipality.name == name)
            .first()
        )

    def get_by_ibge_code(self, ibge_code: str) -> Optional[Municipality]:
        return (
            self.db.query(Municipality)
            .filter(Municipality.ibge_code == ibge_code)
            .first()
        )

    def list_all(self) -> List[Municipality]:
        return self.db.query(Municipality).all()

    def list_active(self) -> List[Municipality]:
        return (
            self.db.query(Municipality)
            .filter(Municipality.active.is_(True))
            .all()
        )

    # ==========================================================
    # UTILITÁRIOS ESTRATÉGICOS
    # ==========================================================

    def exists_by_name(self, name: str) -> bool:
        return (
            self.db.query(Municipality.id)
            .filter(Municipality.name == name)
            .first()
            is not None
        )

    def deactivate(self, municipality: Municipality) -> Municipality:
        """
        Desativa logicamente um município.
        Não remove do banco.
        """
        municipality.active = False
        self.db.commit()
        self.db.refresh(municipality)
        return municipality

    # ==========================================================
    # SUPORTE À GERAÇÃO DE SUPERFÍCIE
    # ==========================================================

    def get_geojson(self, municipality_id: int) -> Optional[dict]:
        municipality = self.get_by_id(municipality_id)
        if municipality:
            return municipality.geojson
        return None

    def get_bbox(self, municipality_id: int) -> Optional[dict]:
        municipality = self.get_by_id(municipality_id)
        if not municipality:
            return None

        return {
            "min_lat": municipality.bbox_min_lat,
            "min_lon": municipality.bbox_min_lon,
            "max_lat": municipality.bbox_max_lat,
            "max_lon": municipality.bbox_max_lon,
        }

    def list_active_for_surface_generation(self) -> List[Municipality]:
        """
        Retorna municípios ativos que possuem bounding box válida.
        Usado pelo scheduler para geração automática de superfície.
        """
        return (
            self.db.query(Municipality)
            .filter(Municipality.active.is_(True))
            .filter(Municipality.bbox_min_lat.isnot(None))
            .filter(Municipality.bbox_min_lon.isnot(None))
            .filter(Municipality.bbox_max_lat.isnot(None))
            .filter(Municipality.bbox_max_lon.isnot(None))
            .all()
        )
