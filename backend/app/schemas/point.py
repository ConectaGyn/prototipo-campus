"""
schemas/point.py

Contratos públicos da API relacionados aos Pontos Críticos
e seus respectivos estados de risco.

Responsabilidade:
- Definir entrada e saída da API
- Refletir modelos ORM (Point, RiskSnapshot)
- Não conter lógica de negócio
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# =====================================================
# SCHEMAS BASE
# =====================================================

class PointBaseSchema(BaseModel):
    """
    Campos estruturais de um ponto crítico.
    Reflete diretamente o modelo ORM.
    """

    name: str = Field(..., description="Nome do ponto crítico")
    latitude: float = Field(..., description="Latitude do ponto")
    longitude: float = Field(..., description="Longitude do ponto")

    active: bool = Field(
        default=True,
        description="Indica se o ponto está ativo para monitoramento",
    )

    influence_radius_m: int = Field(
        default=300,
        description="Raio de influência do ponto em metros",
    )

    neighborhood: Optional[str] = Field(
        default=None,
        description="Bairro ou região administrativa do ponto",
    )

    description: Optional[str] = Field(
        default=None,
        description="Descrição adicional do ponto",
    )


# =====================================================
# SCHEMAS DE ENTRADA
# =====================================================

class PointCreateSchema(PointBaseSchema):
    """
    Schema para criação de novos pontos críticos.
    """
    pass


class PointUpdateSchema(BaseModel):
    """
    Schema para atualização parcial de um ponto crítico.
    Todos os campos são opcionais.
    """

    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    active: Optional[bool] = None
    influence_radius_m: Optional[int] = None
    neighborhood: Optional[str] = None
    description: Optional[str] = None


# =====================================================
# SCHEMAS DE SAÍDA
# =====================================================

class PointResponse(PointBaseSchema):
    """
    Representação pública de um ponto crítico.
    """

    id: str = Field(..., description="Identificador único do ponto")

    municipality_id: Optional[int] = Field(
        default=None,
        description="ID do município associado ao ponto",
    )
    created_at: datetime = Field(
        ..., description="Timestamp de criação do ponto"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp da última atualização do ponto"
    )
    model_config = ConfigDict(from_attributes=True)


class PointListResponse(BaseModel):
    """
    Resposta para listagem de pontos críticos.
    """

    total: int = Field(..., description="Total de pontos retornados")
    items: List[PointResponse]


# =====================================================
# SCHEMA DE RISCO POR PONTO
# =====================================================

class PointRiskResponse(BaseModel):
    """
    Estado de risco associado a um ponto específico.

    Utilizado por:
    - GET /points/{point_id}/risk
    - Map rendering
    """

    point_id: str = Field(..., description="ID do ponto crítico")

    reference_timestamp: datetime = Field(
        ..., description="Timestamp exato da avaliação do risco"
    )

    icra: float = Field(
        ..., description="Índice Climático de Risco de Alagamento"
    )

    icra_std: Optional[float] = Field(
        default=None,
        description="Desvio padrão do ICRA (incerteza do modelo)",
    )

    risk_level: str = Field(
        ..., description="Nível de risco (Baixo, Moderado, Alto, Muito Alto)"
    )

    confidence: str = Field(
        ..., description="Confiança do modelo na inferência"
    )

    expires_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp de validade do risco (se aplicável)",
    )

    model_config = ConfigDict(from_attributes=True)


# =====================================================
# SCHEMA COMBINADO (PONTO + RISCO)
# =====================================================

class PointWithRiskResponse(BaseModel):
    """
    Representação combinada utilizada para mapas
    e dashboards operacionais.
    """

    point: PointResponse
    risk: Optional[PointRiskResponse] = None
