"""
models/risk_surface.py

Modelo responsável por armazenar superfícies espaciais de risco
calculadas para um município em um timestamp específico (bucket global).

Objetivo no produto:
- Permitir renderização contínua (regiões entre pontos) via camada geoespacial
- Servir como cache global (não recalcular por usuário)
- Permitir extração de métricas territoriais (ex: % área em alto risco)
- Escalar para múltiplos municípios, mantendo consistência por ciclo

Notas arquiteturais:
- Este arquivo contém APENAS persistência (ORM), sem cálculos espaciais.
- O payload principal é um GeoJSON (FeatureCollection), persistido em JSONB.
- Garante 1 superfície por (municipality_id, snapshot_timestamp).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    Float,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from backend.app.database import Base


class RiskSurface(Base):
    """
    Superfície espacial de risco associada a um município e a um ciclo global.
    """

    __tablename__ = "risk_surfaces"

    # =====================================================
    # IDENTIFICAÇÃO
    # =====================================================

    id = Column(Integer, primary_key=True)

    municipality_id = Column(
        Integer,
        ForeignKey("municipalities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Município ao qual esta superfície pertence",
    )

    snapshot_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Timestamp global do ciclo (mesmo conceito de RiskSnapshot)",
    )

    # =====================================================
    # DADOS DA SUPERFÍCIE (GeoJSON)
    # =====================================================

    geojson = Column(
        JSONB,
        nullable=False,
        doc="GeoJSON (FeatureCollection) representando a superfície de risco",
    )

    # =====================================================
    # METADADOS TÉCNICOS 
    # =====================================================

    grid_resolution_m = Column(
        Integer,
        nullable=False,
        doc="Resolução espacial usada (ex: 500m)",
    )

    kernel_sigma_m = Column(
        Integer,
        nullable=False,
        doc="Sigma do kernel em metros (adaptativo por densidade de pontos)",
    )

    total_cells = Column(
        Integer,
        nullable=True,
        doc="Quantidade total de células/tiles gerados (se aplicável)",
    )

    # =====================================================
    # MÉTRICAS TERRITORIAIS 
    # =====================================================

    total_area_m2 = Column(
        Float,
        nullable=True,
        doc="Área total considerada (interseção do município com a grade)",
    )

    high_risk_area_m2 = Column(
        Float,
        nullable=True,
        doc="Área total classificada como alto/muito alto risco",
    )

    high_risk_percentage = Column(
        Float,
        nullable=True,
        doc="Percentual da área total em alto/muito alto risco (0-100)",
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
        doc="Timestamp de validade da superfície (TTL alinhado ao snapshot)",
    )

    source = Column(
        String(20),
        nullable=False,
        default="scheduled",
        doc="Origem: scheduled | manual | on_demand (se no futuro existir)",
    )

    # =====================================================
    # RELACIONAMENTOS
    # =====================================================

    municipality = relationship(
        "Municipality",
        backref="risk_surfaces",
        lazy="joined",
    )

    # =====================================================
    # CONSTRAINTS E ÍNDICES
    # =====================================================

    __table_args__ = (
        # 1 superfície por município por ciclo
        UniqueConstraint(
            "municipality_id",
            "snapshot_timestamp",
            name="uq_municipality_surface_timestamp",
        ),
        # índice combinado para consultas rápidas (município + ciclo)
        Index(
            "idx_municipality_surface_timestamp",
            "municipality_id",
            "snapshot_timestamp",
        ),
    )

    # =====================================================
    # REPRESENTAÇÃO
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<RiskSurface("
            f"municipality_id={self.municipality_id}, "
            f"snapshot_timestamp={self.snapshot_timestamp}, "
            f"grid_resolution_m={self.grid_resolution_m}, "
            f"kernel_sigma_m={self.kernel_sigma_m}"
            f")>"
        )
