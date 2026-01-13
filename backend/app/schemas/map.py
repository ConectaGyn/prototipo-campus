"""
map.py

Schemas relacionados à visualização do mapa e estado atual
dos pontos críticos monitorados.

Define os contratos entre backend e frontend para o módulo
de mapa, separando claramente:
- dados espaciais
- estado de risco 
"""

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.point import PointResponse


# =====================================================
# SCHEMAS DE RISCO
# =====================================================

class RiskStatusSchema(BaseModel):
    """
    Estado de risco atual associado a um ponto crítico.

    Este schema é utilizado:
    - quando o risco já foi calculado para o ponto
    - ou quando o frontend solicita risco sob demanda
    """

    icra: float = Field(
        ...,
        ge=0,
        le=1,
        description="Índice Composto de Risco de Alagamento (0 a 1)",
        example=0.72,
    )

    nivel: str = Field(
        ...,
        description="Classificação qualitativa do risco (Baixo, Moderado, Alto, Muito Alto)",
        example="Alto",
    )

    confianca: str = Field(
        ...,
        description="Nível de confiança da previsão",
        example="Alta",
    )

    cor: str = Field(
        ...,
        description="Cor associada ao risco para visualização no mapa",
        example="vermelho",
    )


# =====================================================
# SCHEMA DE PONTO NO MAPA
# =====================================================

class MapPointSchema(BaseModel):
    """
    Representação de um ponto no contexto do mapa.

    - sempre contém dados de localização
    - pode ou não conter risco atual associado
    """

    ponto: PointResponse = Field(
        ...,
        description="Informações básicas e localização do ponto crítico",
    )

    risco_atual: Optional[RiskStatusSchema] = Field(
        None,
        description=("Estado de risco atual do ponto.",
        "Pode ser nulo quando o risco não foi calculado ainda.", 
        "Ou quando o frontend solicita apenas dados de localização."
        ),
    )


# =====================================================
# SCHEMA DE RESPOSTA DO MAPA
# =====================================================

class MapPointsResponse(BaseModel):
    """
    Resposta do endpoint /map/points.

    Utilizada para renderização inicial do mapa no frontend,
    """

    pontos: List[MapPointSchema] = Field(
        ...,
        description="Lista de pontos críticos para exibição no mapa",
    )

    atualizado_em: datetime = Field(
        ...,
        description="Timestamp da última atualização dos dados",
        example="2026-01-07T06:30:00Z",
    )
