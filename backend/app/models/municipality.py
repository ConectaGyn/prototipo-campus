"""
models/municipality.py

Modelo responsável por representar um município monitorado
pelo sistema ClimaGyn.

Responsabilidades:
- Armazenar dados institucionais do município
- Persistir o polígono oficial (GeoJSON)
- Fornecer bounding box para otimização espacial
- Servir como base para cálculo de superfícies de risco

Arquitetura híbrida:
- GeoJSON versionado no repositório
- Copiado e persistido no banco (JSON/JSONB)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Float,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from backend.app.database import Base


class Municipality(Base):
    """
    Representa um município monitorado pelo sistema.
    Podem existir múltiplos municípios, cada um possui seu próprio polígono oficial.
    """

    __tablename__ = "municipalities"

    # =====================================================
    # IDENTIFICAÇÃO
    # =====================================================

    id = Column(Integer, primary_key=True)

    name = Column(
        String(120),
        nullable=False,
        unique=True,
        doc="Nome oficial do município",
    )

    ibge_code = Column(
        String(10),
        nullable=True,
        index=True,
        doc="Código IBGE do município",
    )

    active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Indica se o município está ativo no monitoramento",
    )

    # =====================================================
    # GEOMETRIA
    # =====================================================

    # Compatível com SQLite e PostgreSQL
    geojson = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        doc="Polígono oficial do município (GeoJSON - type Polygon ou MultiPolygon)",
    )

    bbox_min_lat = Column(Float, nullable=False)
    bbox_min_lon = Column(Float, nullable=False)
    bbox_max_lat = Column(Float, nullable=False)
    bbox_max_lon = Column(Float, nullable=False)

    # =====================================================
    # CONTROLE OPERACIONAL
    # =====================================================

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # =====================================================
    # ÍNDICES
    # =====================================================

    __table_args__ = (
        Index("idx_municipality_active", "active"),
    )

    # =====================================================
    # REPRESENTAÇÃO
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<Municipality("
            f"id={self.id}, "
            f"name={self.name}, "
            f"ibge={self.ibge_code}"
            f")>"
        )
