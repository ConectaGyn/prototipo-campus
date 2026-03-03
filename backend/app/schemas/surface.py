"""
schemas/surface.py

Schemas Pydantic responsáveis pelos contratos de API
relacionados à superfície espacial de risco.

Este arquivo:
- NÃO contém lógica de negócio
- NÃO acessa banco
- NÃO calcula nada
- Define apenas contratos de entrada/saída da API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ============================================================
# STATS
# ============================================================

class SurfaceStatsSchema(BaseModel):
    """
    Estatísticas agregadas da superfície.
    """

    total_cells: Optional[int] = Field(
        default=None,
        description="Total de células geradas no grid."
    )

    total_area_m2: Optional[float] = Field(
        default=None,
        description="Área total considerada (m²)."
    )

    high_risk_area_m2: Optional[float] = Field(
        default=None,
        description="Área total classificada como alto risco (m²)."
    )

    high_risk_percentage: Optional[float] = Field(
        default=None,
        description="Percentual da área total classificada como alto risco."
    )

    class Config:
        from_attributes = True


# ============================================================
# METADATA
# ============================================================

class SurfaceMetadataSchema(BaseModel):
    """
    Metadados técnicos da superfície.
    """

    computed_at: datetime = Field(
        description="Timestamp UTC de quando a superfície foi calculada."
    )

    valid_until: Optional[datetime] = Field(
        default=None,
        description="Timestamp UTC de validade da superfície."
    )

    source: str = Field(
        description="Origem da geração (scheduler | on_demand | manual)."
    )

    class Config:
        from_attributes = True


# ============================================================
# RESPONSE PRINCIPAL
# ============================================================

class SurfaceResponseSchema(BaseModel):
    """
    Envelope completo retornado pelo endpoint de superfície.
    """

    municipality_id: int = Field(
        description="ID interno do município."
    )

    snapshot_timestamp: datetime = Field(
        description="Timestamp de referência do ciclo de risco (UTC)."
    )

    grid_resolution_m: int = Field(
        description="Resolução do grid em metros."
    )

    kernel_sigma_m: int = Field(
        description="Sigma utilizado no modelo Kernel (metros)."
    )

    geojson: Dict[str, Any] = Field(
        description="GeoJSON completo da superfície interpolada."
    )

    stats: SurfaceStatsSchema = Field(
        description="Estatísticas agregadas da superfície."
    )

    metadata: SurfaceMetadataSchema = Field(
        description="Metadados técnicos da geração."
    )

    class Config:
        from_attributes = True


# ============================================================
# RESPONSE DE RECOMPUTE
# ============================================================

class SurfaceRecomputeResponseSchema(BaseModel):
    """
    Resposta simples para recompute manual.
    """

    status: str = Field(
        description="Status da operação (recomputed)."
    )

    municipality_id: int = Field(
        description="ID do município recalculado."
    )

    snapshot_timestamp: datetime = Field(
        description="Timestamp UTC do ciclo recalculado."
    )
