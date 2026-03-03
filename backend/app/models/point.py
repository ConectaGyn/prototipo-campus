"""
models/point.py

Modelo ORM (SQLAlchemy) para Pontos Críticos de Alagamento.

Este modelo representa a FONTE DE VERDADE dos pontos críticos no backend:
- Persistido em PostgreSQL
- Usado pelo scheduler para calcular snapshots periódicos
- Consumido pelo frontend para renderização do mapa

Notas:
- Este arquivo contém APENAS a definição do modelo (sem regras de negócio).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import relationship

from sqlalchemy import (
    Boolean, 
    DateTime, 
    Float, 
    Integer, 
    String, 
    Text, 
    func, 
    ForeignKey,)
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database import Base


class Point(Base):
    """
    Ponto crítico persistido no banco.

    Convenções:
    - id: identificador lógico (string) para manter compatibilidade com o CSV/legado (ex: "P_001", "grid_-16.695_-49.295")
    - latitude/longitude: coordenadas do ponto
    - active: permite desativar sem apagar histórico
    - influence_radius_m: raio operacional 
    """

    __tablename__ = "points"

    # -----------------------
    # Identificação
    # -----------------------
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)

    municipality_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("municipalities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # -----------------------
    # Localização
    # -----------------------
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # -----------------------
    # Metadados operacionais
    # -----------------------
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    influence_radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # -----------------------
    # Classificação/descrição
    # -----------------------
    neighborhood: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # -----------------------
    # Auditoria
    # -----------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    risk_snapshots = relationship(
        "RiskSnapshot",
        back_populates="point",
        cascade="all, delete-orphan",
    )

    municipality = relationship(
        "Municipality",
        backref="points",
        lazy="joined",
    )

    # -----------------------
    # Helpers simples (sem negócio)
    # -----------------------
    def coordinates(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)

    def to_feature_payload(self) -> dict:
        """
        Payload mínimo para serviços que constroem features ou chamam IA.
        """
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "influence_radius_m": self.influence_radius_m,
            "neighborhood": self.neighborhood,
        }
