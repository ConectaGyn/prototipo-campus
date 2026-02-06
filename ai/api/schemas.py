"""
schemas.py

Define os schemas (contratos) de entrada e saída da API de IA.
Utiliza Pydantic para validação, tipagem e documentação automática.
"""

from typing import List, Dict, Optional
from datetime import date

from pydantic import BaseModel, Field


# ================================
# FEATURES DO MODELO ICRA
# ================================

class ICRAFeatures(BaseModel):
    """
    Features esperadas pelo modelo ICRA.
    A ordem e os nomes devem ser preservados na inferência.
    """

    precipitacao_total_mm: float
    precipitacao_ma_7d: float
    precipitacao_ma_30d: float
    precipitacao_ma_90d: float

    anomalia_precip_7d: float
    anomalia_precip_30d: float

    intensidade_precipitacao: float

    precipitacao_lag_1d: float
    precipitacao_lag_2d: float
    precipitacao_lag_3d: float
    precipitacao_lag_7d: float
    precipitacao_lag_14d: float
    precipitacao_lag_30d: float

    temperatura_media_2m_C: float
    temperatura_aparente_media_2m_C: float
    temperatura_lag_1d: float
    temperatura_lag_7d: float

    mes_sin: float
    mes_cos: float
    dia_sin: float
    dia_cos: float


# ================================
# INPUT SCHEMA
# ================================

class ICRAPredictRequest(BaseModel):
    """
    Payload de entrada para predição de risco ICRA.
    """

    data: date = Field(..., description="Data de referência da previsão")

    features: ICRAFeatures = Field(
        ...,
        description="Conjunto completo de features exigidas pelo modelo ICRA"
    )

    ponto: Optional[str] = Field(
        None,
        description="Identificador opcional do ponto crítico"
    )


# ================================
# OUTPUT SCHEMAS
# ================================

class ICRADetails(BaseModel):
    """
    Informações auxiliares para interpretação do risco.
    """

    chuva_dia: float = Field(..., description="Precipitação do dia (mm)")
    chuva_30d: float = Field(..., description="Média móvel de precipitação 30 dias (mm)")
    chuva_90d: float = Field(..., description="Média móvel de precipitação 90 dias (mm)")


class ICRAPredictResponse(BaseModel):
    """
    Resposta final da API para predição de risco.
    """

    data: date = Field(..., description="Data da previsão")

    icra: float = Field(
        ...,
        ge=0,
        le=1,
        description="Índice Composto de Risco de Alagamento (0 a 1)"
    )

    icra_std: Optional[float] = Field(
        None,
        ge=0,
        description="Incerteza associada à previsão"
    )

    nivel_risco: str = Field(
        ...,
        description="Classificação qualitativa do risco"
    )

    confianca: str = Field(
        ...,
        description="Nível de confiança da previsão"
    )

    detalhes: ICRADetails = Field(
        ...,
        description="Detalhes hidrometeorológicos relevantes"
    )


# ================================
# METADATA / HEALTHCHECK
# ================================

class ICRAThresholds(BaseModel):
    baixo_max: float
    moderado_max: float
    alto_max: float
    descricao: Dict[str, str]

class ModelInfoResponse(BaseModel):
    """
    Informações básicas sobre o modelo carregado.
    """

    modelo: str
    versao: str
    features: List[str]
    thresholds: ICRAThresholds

class HealthCheckResponse(BaseModel):
    """
    Resposta padrão para verificação de saúde da API.
    """

    status: str = "ok"
