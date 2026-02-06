"""
point.py

Schemas de API relacionados aos Pontos Críticos de Alagamento.

Responsável apenas por definir contratos de entrada e saída
da API. Não contém lógica de domínio.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ================================
# SCHEMAS BÁSICOS
# ================================

class GeoLocationSchema(BaseModel):
    """
    Coordenadas geográficas de um ponto.
    """

    latitude: float = Field(..., description="Latitude do ponto")
    longitude: float = Field(..., description="Longitude do ponto")


# ================================
# SCHEMAS DE SAÍDA
# ================================

class PointResponse(BaseModel):
    """
    Representação pública de um ponto crítico.
    """

    id: str = Field(..., description="Identificador único do ponto")
    nome: str = Field(..., description="Nome do ponto crítico")

    localizacao: GeoLocationSchema = Field(
        ..., description="Coordenadas geográficas do ponto"
    )

    ativo: bool = Field(
        True,
        description="Indica se o ponto está ativo para monitoramento"
    )

    raio_influencia_m: int = Field(
        300,
        description="Raio de influência do ponto em metros"
    )

    bairro: Optional[str] = Field(
        None,
        description="Bairro ou região do ponto"
    )

    descricao: Optional[str] = Field(
        None,
        description="Descrição adicional do ponto"
    )

    class Config:
        orm_mode = True


# ================================
# SCHEMAS DE LISTAGEM
# ================================

class PointListResponse(BaseModel):
    """
    Resposta para listagem de pontos críticos.
    """

    total: int = Field(..., description="Total de pontos retornados")
    pontos: List[PointResponse]

# ================================
# SCHEMA DE RISCO POR PONTO
# ================================

class PointRiskSchema(BaseModel):
    """
    Resposta do cálculo de risco para um ponto específico.

    Utilizado  pelo endpoint:
    GET /map/points/{point_id}/risk
    """

    icra: float = Field(
        ...,
        description="Índice Climático de Risco de Alagamento (ICRA)",
    )
    nivel: str = Field(
        ...,
        description="Nível risco calculado (Baixo, Moderado, Alto, Muito Alto)",
    )
    confianca: str = Field(
        ...,
        description="Grau de confiança do modelo da inferência",
    )
    cor: str = Field(
        ...,
        description="Cor associada ao nível de risco",
    )