"""
risk_repository.py

Camada de acesso a dados para snapshots de risco.

Responsável exclusivamente por:
- Persistência de RiskSnapshot
- Consultas por ponto
- Consultas por timestamp
- Operações de bulk insert/update

Não contém lógica de negócio.
Não realiza chamadas externas.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, desc, func, distinct
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.models.risk_snapshot import RiskSnapshot


class RiskRepository:
    """
    Repositório para manipulação de snapshots de risco.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==========================================================
    # INSERT / UPDATE (UPSERT)
    # ==========================================================

    def save_snapshot(self, snapshot: RiskSnapshot) -> RiskSnapshot:
        """
        Salva ou atualiza snapshot individual.

        Garante unicidade por:
            (point_id, snapshot_timestamp)
        """

        try:
            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)
            return snapshot

        except IntegrityError:
            self.db.rollback()

            existing = self._get_by_point_and_timestamp(
                snapshot.point_id,
                snapshot.snapshot_timestamp,
            )

            if not existing:
                raise

            # Atualiza campos mutáveis
            existing.icra = snapshot.icra
            existing.icra_std = snapshot.icra_std
            existing.nivel_risco = snapshot.nivel_risco
            existing.confianca = snapshot.confianca
            existing.chuva_dia = snapshot.chuva_dia
            existing.chuva_30d = snapshot.chuva_30d
            existing.chuva_90d = snapshot.chuva_90d
            existing.source = snapshot.source

            self.db.commit()
            self.db.refresh(existing)

            return existing

    def bulk_save_snapshots(self, snapshots: List[RiskSnapshot]) -> None:
        """
        Salva múltiplos snapshots em uma única transação
        """
        try:
            self.db.add_all(snapshots)
            self.db.commit()

        except IntegrityError:
            self.db.rollback()

            for snapshot in snapshots:
                self.save_snapshot(snapshot)

    # ==========================================================
    # CONSULTAS
    # ==========================================================

    def get_latest_by_point(self, point_id: str) -> Optional[RiskSnapshot]:
        """
        Retorna snapshot mais recente de um ponto específico.
        """

        stmt = (
            select(RiskSnapshot)
            .where(RiskSnapshot.point_id == point_id)
            .order_by(desc(RiskSnapshot.snapshot_timestamp))
            .limit(1)
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def get_snapshot(
        self,
        point_id: str,
        snapshot_timestamp: datetime,
    ) -> Optional[RiskSnapshot]:
        """
        Retorna snapshot exato de um ponto para um timestamp específico.
        """

        stmt = (
            select(RiskSnapshot)
            .where(
                RiskSnapshot.point_id == point_id,
                RiskSnapshot.snapshot_timestamp == snapshot_timestamp,
            )
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_bucket_timestamp(self) -> Optional[datetime]:
        """
        Retorna o timestamp global mais recente disponível no sistema.
        """

        stmt = (
            select(RiskSnapshot.snapshot_timestamp)
            .order_by(desc(RiskSnapshot.snapshot_timestamp))
            .limit(1)
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_bucket_timestamp_for_points(
        self,
        point_ids: List[str],
    ) -> Optional[datetime]:
        """
        Retorna o timestamp mais recente contendo ao menos um snapshot dos pontos informados.
        """
        if not point_ids:
            return None

        stmt = (
            select(RiskSnapshot.snapshot_timestamp)
            .where(RiskSnapshot.point_id.in_(point_ids))
            .order_by(desc(RiskSnapshot.snapshot_timestamp))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_complete_bucket_timestamp(
        self,
        point_ids: List[str],
    ) -> Optional[datetime]:
        """
        Retorna o bucket mais recente que contém snapshots para TODOS os pontos informados.
        """
        if not point_ids:
            return None

        expected = len(set(point_ids))
        stmt = (
            select(RiskSnapshot.snapshot_timestamp)
            .where(RiskSnapshot.point_id.in_(point_ids))
            .group_by(RiskSnapshot.snapshot_timestamp)
            .having(func.count(distinct(RiskSnapshot.point_id)) == expected)
            .order_by(desc(RiskSnapshot.snapshot_timestamp))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_snapshots_by_bucket(
        self,
        snapshot_timestamp: datetime,
    ) -> List[RiskSnapshot]:
        """
        Retorna todos os snapshots de um timestamp específico.
        Utilizado pelo endpoint /map/points.
        """

        stmt = (
            select(RiskSnapshot)
            .where(RiskSnapshot.snapshot_timestamp == snapshot_timestamp)
        )

        return self.db.execute(stmt).scalars().all()
    
    def get_snapshot_for_update(
            self,
            point_id: str,
            snapshot_timestamp: datetime,
    ):
            stmt = (
                select(RiskSnapshot)
                .where(
                    RiskSnapshot.point_id == point_id,
                    RiskSnapshot.snapshot_timestamp == snapshot_timestamp,
                )
                .with_for_update()
            )

            return self.db.execute(stmt).scalar_one_or_none()

    def get_history_by_point(
        self,
        point_id: str,
        limit: int = 100,
    ) -> List[RiskSnapshot]:
        """
        Retorna histórico de snapshots de um ponto.
        """

        stmt = (
            select(RiskSnapshot)
            .where(RiskSnapshot.point_id == point_id)
            .order_by(desc(RiskSnapshot.snapshot_timestamp))
            .limit(limit)
        )

        return self.db.execute(stmt).scalars().all()

    # ==========================================================
    # MÉTODO PRIVADO
    # ==========================================================

    def _get_by_point_and_timestamp(
        self,
        point_id: str,
        snapshot_timestamp: datetime,
    ) -> Optional[RiskSnapshot]:
        """
        Busca snapshot específico por (point_id, snapshot_timestamp).
        """

        stmt = (
            select(RiskSnapshot)
            .where(
                RiskSnapshot.point_id == point_id,
                RiskSnapshot.snapshot_timestamp == snapshot_timestamp,
            )
        )

        return self.db.execute(stmt).scalar_one_or_none()
