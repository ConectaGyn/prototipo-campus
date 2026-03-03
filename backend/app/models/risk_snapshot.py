"""
models/risk_snapshot.py

Modelo responsável por armazenar snapshots de risco
calculados para pontos críticos em timestamps específicos.

Permite:
- Histórico completo por ponto
- Cache global para todos usuários
- Atualização automática via scheduler
- Consulta eficiente por bucket (reference_ts)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


class RiskSnapshot(Base):
    """
    Snapshot de risco para um ponto crítico em um timestamp exato.

    Cada registro representa o estado do risco calculado
    para um ponto específico em um ciclo global (reference_ts).
    """

    __tablename__ = "risk_snapshots"

    # =====================================================
    # IDENTIFICAÇÃO
    # =====================================================

    id = Column(Integer, primary_key=True)

    point_id = Column(
        String(64),
        ForeignKey("points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    snapshot_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Timestamp global do ciclo (ex: bucket 3h)",
    )

    # =====================================================
    # RESULTADO DO MODELO DE IA
    # =====================================================

    icra = Column(
        Float,
        nullable=False,
        doc="Índice Climático de Risco de Alagamento",
    )

    icra_std = Column(
        Float,
        nullable=True,
        doc="Desvio padrão associado à predição",
    )

    nivel_risco = Column(
        String(50),
        nullable=False,
        doc="Classificação textual do risco",
    )

    confianca = Column(
        String(50),
        nullable=True,
        doc="Nível de confiança do modelo",
    )

    # =====================================================
    # DETALHES AUXILIARES (resumo climático)
    # =====================================================

    chuva_dia = Column(
        Float,
        nullable=True,
        doc="Precipitação no dia do cálculo",
    )

    chuva_30d = Column(
        Float,
        nullable=True,
        doc="Média/acumulado em 30 dias",
    )

    chuva_90d = Column(
        Float,
        nullable=True,
        doc="Média/acumulado em 90 dias",
    )

    # =====================================================
    # CONTROLE OPERACIONAL
    # =====================================================

    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Momento real do cálculo",
    )

    valid_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp de validade do snapshot",
    )

    source = Column(
        String(20),
        nullable=False,
        default="scheduled",
        doc="Origem do snapshot: scheduled ou on_demand",
    )

    # =====================================================
    # RELACIONAMENTO
    # =====================================================

    point = relationship(
        "Point",
        back_populates="risk_snapshots",
        lazy="joined",
    )

    # =====================================================
    # CONSTRAINTS E ÍNDICES
    # =====================================================

    __table_args__ = (
        # Garante 1 snapshot por ponto por ciclo
        UniqueConstraint(
            "point_id",
            "snapshot_timestamp",
            name="uq_point_snapshot_timestamp",
        ),
        # Índice otimizado para consulta por ponto + ciclo
        Index(
            "idx_point_snapshot_timestamp",
            "point_id",
            "snapshot_timestamp",
        ),
    )

    # =====================================================
    # REPRESENTAÇÃO
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<RiskSnapshot("
            f"point_id={self.point_id}, "
            f"snapshot_timestamp={self.snapshot_timestamp}, "
            f"icra={self.icra}, "
            f"nivel={self.nivel_risco}"
            f")>"
        )
