"""
repositories/risk_surface_repository.py

Camada de acesso a dados para superfícies espaciais de risco.

Responsabilidades:
- Persistência de superfícies (create)
- Consulta por município
- Consulta por validade (TTL lógico)
- Histórico temporal
- Suporte ao scheduler e rotas

IMPORTANTE:
- NÃO contém lógica de cálculo espacial
- NÃO decide quando recalcular
- NÃO contém regras de negócio
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, desc, and_, or_

from backend.app.models.risk_surface import RiskSurface


class RiskSurfaceRepository:
    """
    Repositório de persistência das superfícies espaciais de risco.
    """

    def __init__(self, session: Session):
        self.session = session

    # ==========================================================
    # CREATE/SAVE
    # ==========================================================
    
    def save_surface(self, surface: RiskSurface) -> RiskSurface:
        """
        Salva superfície com proteção contra corrida (idempotente).
        Se já existir superfície com mesma chave composta,
        retorna a existente.
        """

        try:
            self.session.add(surface)
            self.session.commit()
            self.session.refresh(surface)
            return surface

        except IntegrityError:
            self.session.rollback()

            existing = self.get_by_municipality_and_timestamp(
                municipality_id=surface.municipality_id,
                snapshot_timestamp=surface.snapshot_timestamp,
            )

            if existing:
                return existing
            raise

    def replace_surface(self, surface: RiskSurface) -> RiskSurface:
        """
        Substitui superfície existente para a mesma chave composta.
        Usado quando force_recompute=True.
        """

        existing = self.get_by_municipality_and_timestamp(
            municipality_id=surface.municipality_id,
            snapshot_timestamp=surface.snapshot_timestamp,
        )
        
        if existing:
            self.session.delete(existing)
            self.session.flush()  # garante remoção antes do insert

        self.session.add(surface)
        self.session.commit()
        self.session.refresh(surface)
        return surface


    # ==========================================================
    # GETs
    # ==========================================================

    def get_by_id(self, surface_id: int) -> Optional[RiskSurface]:
        """
        Retorna superfície por ID primário.
        """
        stmt = select(RiskSurface).where(RiskSurface.id == surface_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_municipality_and_timestamp(
            self,
            municipality_id: int,
            snapshot_timestamp: datetime,
            ) -> Optional[RiskSurface]:
        """
        Retorna superfície específica por município + snapshot_timestamp.
        """

        stmt = (
            select(RiskSurface)
            .where(
                and_(
                    RiskSurface.municipality_id == municipality_id,
                    RiskSurface.snapshot_timestamp == snapshot_timestamp,
                )
            )
            .limit(1)
        )

        return self.session.execute(stmt).scalar_one_or_none()

    def get_latest_by_municipality(
        self,
        municipality_id: int,
    ) -> Optional[RiskSurface]:
        """
        Retorna a superfície mais recente para um município,
        independentemente de validade.
        """
        stmt = (
            select(RiskSurface)
            .where(RiskSurface.municipality_id == municipality_id)
            .order_by(desc(RiskSurface.snapshot_timestamp))
            .limit(1)
        )

        return self.session.execute(stmt).scalar_one_or_none()

    def get_latest_valid_by_municipality(
        self,
        municipality_id: int,
        reference_time: Optional[datetime] = None,
    ) -> Optional[RiskSurface]:
        """
        Retorna a superfície válida mais recente para um município.

        Critério de validade:
        - valid_until IS NULL
        OR
        - valid_until >= reference_time (default = now UTC)
        """

        if reference_time is None:
            reference_time = datetime.now().astimezone()

        stmt = (
            select(RiskSurface)
            .where(
                and_(
                    RiskSurface.municipality_id == municipality_id,
                    or_(
                        RiskSurface.valid_until.is_(None),
                        RiskSurface.valid_until >= reference_time,
                    ),
                )
            )
            .order_by(desc(RiskSurface.snapshot_timestamp))
            .limit(1)
        )

        return self.session.execute(stmt).scalar_one_or_none()
    
    # ==========================================================
    # VALIDADE (TTL lógico)
    # ==========================================================

    def is_valid(
            self,
            surface: RiskSurface,
            now: Optional[datetime] = None,
    ) -> bool:
        """
        Verifica se a superfície ainda está válida (TTL).
        """

        if now is None:
            now = datetime.now(timezone.utc)

        if surface.valid_until is None:
            return True

        return surface.valid_until >= now


    # ==========================================================
    # List / Delete / Exists
    # ==========================================================

    def list_by_municipality(
        self,
        municipality_id: int,
        limit: Optional[int] = None,
    ) -> List[RiskSurface]:
        """
        Lista superfícies históricas de um município,
        ordenadas da mais recente para a mais antiga.
        """

        stmt = (
            select(RiskSurface)
            .where(RiskSurface.municipality_id == municipality_id)
            .order_by(desc(RiskSurface.snapshot_timestamp))
        )

        if limit:
            stmt = stmt.limit(limit)

        return list(self.session.execute(stmt).scalars().all())

    def list_recent(
        self,
        limit: int = 50,
    ) -> List[RiskSurface]:
        """
        Lista superfícies recentes globalmente (todos municípios).
        Útil para dashboards administrativos.
        """

        stmt = (
            select(RiskSurface)
            .order_by(desc(RiskSurface.snapshot_timestamp))
            .limit(limit)
        )

        return list(self.session.execute(stmt).scalars().all())

    def delete(self, surface: RiskSurface) -> None:
        """
        Remove uma superfície específica.
        Uso administrativo ou manutenção.
        """
        self.session.delete(surface)
        self.session.commit()

    def exists_for_municipality(
        self,
        municipality_id: int,
    ) -> bool:
        """
        Verifica se existe qualquer superfície registrada
        para o município.
        """

        stmt = (
            select(RiskSurface.id)
            .where(RiskSurface.municipality_id == municipality_id)
            .limit(1)
        )

        result = self.session.execute(stmt).first()
        return result is not None
