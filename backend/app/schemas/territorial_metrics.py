"""
territorial_metrics.py

Schemas da camada de Inteligência Territorial do ClimaGyn.

Responsabilidade:
- Definir contratos de saída da API de analytics
- Estruturar envelope institucional de métricas territoriais
- Não conter lógica matemática
- Não acessar banco
- Não conter regra de negócio
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# MUNICIPALITY INFO
# ============================================================

class MunicipalityInfoSchema(BaseModel):
    """
    Informações resumidas do município analisado.
    """

    id: int = Field(..., description="Identificador interno do município")
    name: str = Field(..., description="Nome oficial do município")
    ibge_code: Optional[str] = Field(
        None,
        description="Código IBGE do município",
    )
    active: bool = Field(
        ...,
        description="Indica se o município está ativo no monitoramento",
    )

    bbox_min_lat: float = Field(..., description="Latitude mínima do bounding box")
    bbox_min_lon: float = Field(..., description="Longitude mínima do bounding box")
    bbox_max_lat: float = Field(..., description="Latitude máxima do bounding box")
    bbox_max_lon: float = Field(..., description="Longitude máxima do bounding box")

    updated_at: datetime = Field(
        ...,
        description="Timestamp da última atualização cadastral do município",
    )

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# SURFACE METADATA
# ============================================================

class SurfaceInfoSchema(BaseModel):
    """
    Metadados técnicos da superfície de risco utilizada na análise.
    """

    snapshot_timestamp: datetime = Field(
        ...,
        description="Timestamp exato do snapshot da superfície analisada",
    )

    valid_until: Optional[datetime] = Field(
        None,
        description="Momento em que o snapshot deixa de ser considerado válido",
    )

    grid_resolution_m: int = Field(
        ...,
        gt=0,
        description="Resolução da grade espacial em metros",
    )

    kernel_sigma_m: int = Field(
        ...,
        gt=0,
        description="Parâmetro sigma do kernel gaussiano utilizado",
    )

    total_cells: Optional[int] = Field(
        None,
        ge=0,
        description="Quantidade total de células na superfície",
    )

    total_area_m2: Optional[float] = Field(
        None,
        ge=0,
        description="Área total coberta pela superfície (m²)",
    )

    high_risk_area_m2: Optional[float] = Field(
        None,
        ge=0,
        description="Área classificada como alto risco (m²)",
    )

    high_risk_percentage: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Percentual da área total classificada como alto risco (0 a 1)",
    )

    source: str = Field(
        ...,
        description="Origem do snapshot (ex: scheduler, on_demand)",
    )


# ============================================================
# SURFACE SUMMARY (AGREGADO ESTATÍSTICO)
# ============================================================

class SurfaceSummarySchema(BaseModel):
    """
    Estatísticas agregadas da superfície de risco.
    """

    total_area_m2: float = Field(
        ...,
        ge=0,
        description="Área total analisada (m²)",
    )

    high_risk_area_m2: float = Field(
        ...,
        ge=0,
        description="Área classificada como alto risco (m²)",
    )

    high_risk_percentage: float = Field(
        ...,
        ge=0,
        le=1,
        description="Percentual da área em alto risco (0 a 1)",
    )

    mean_icra: float = Field(
        ...,
        ge=0,
        le=1,
        description="Valor médio do ICRA na superfície",
    )

    median_icra: float = Field(
        ...,
        ge=0,
        le=1,
        description="Mediana do ICRA na superfície",
    )

    max_icra: float = Field(
        ...,
        ge=0,
        le=1,
        description="Valor máximo de ICRA identificado",
    )

    std_icra: float = Field(
        ...,
        ge=0,
        description="Desvio padrão do ICRA (heterogeneidade espacial)",
    )

    total_cells: int = Field(
        ...,
        ge=0,
        description="Quantidade total de células da grade",
    )

    high_risk_cells: int = Field(
        ...,
        ge=0,
        description="Quantidade de células classificadas como alto risco",
    )


# ============================================================
# TERRITORIAL METRICS (INTELIGÊNCIA ESTRATÉGICA)
# ============================================================

class TerritorialMetricsSchema(BaseModel):
    """
    Indicadores estratégicos de criticidade territorial.

    Esses índices são derivados da superfície de risco
    e transformam dados técnicos em indicadores de gestão.
    """

    severity_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Intensidade média ponderada do risco territorial (0 a 1)",
    )

    criticality_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Score composto de criticidade territorial (0 a 1)",
    )

    dispersion_index: float = Field(
        ...,
        ge=0,
        description="Índice de dispersão espacial do risco",
    )

    exposure_index: float = Field(
        ...,
        ge=0,
        le=1,
        description="Proporção territorial exposta a alto risco (0 a 1)",
    )

    risk_classification: str = Field(
        ...,
        description="Classificação estratégica final (Baixo, Moderado, Alto, Crítico)",
    )


# ============================================================
# ENVELOPE PRINCIPAL (RESPOSTA UNITÁRIA)
# ============================================================

class TerritorialMetricsResponseSchema(BaseModel):
    """
    Resposta principal de métricas territoriais.

    Endpoint típico:
    GET /analytics/municipalities/{id}/metrics
    """

    municipality: MunicipalityInfoSchema
    surface: SurfaceInfoSchema

    high_risk_threshold: float = Field(
        ...,
        ge=0,
        le=1,
        description="Threshold utilizado para classificar alto risco (ex: 0.7)",
    )

    surface_summary: SurfaceSummarySchema
    territorial_metrics: TerritorialMetricsSchema


# ============================================================
# SÉRIE TEMPORAL
# ============================================================

class TerritorialMetricsSeriesItemSchema(BaseModel):
    """
    Item individual de série temporal de métricas territoriais.
    """

    snapshot_timestamp: datetime = Field(
        ...,
        description="Timestamp do snapshot analisado",
    )

    surface_summary: SurfaceSummarySchema
    territorial_metrics: TerritorialMetricsSchema


class TerritorialMetricsSeriesResponseSchema(BaseModel):
    """
    Resposta de série histórica de métricas territoriais.
    """

    municipality: MunicipalityInfoSchema

    total: int = Field(
        ...,
        ge=0,
        description="Quantidade total de snapshots retornados",
    )

    high_risk_threshold: float = Field(
        ...,
        ge=0,
        le=1,
        description="Threshold utilizado para classificação",
    )

    series: List[TerritorialMetricsSeriesItemSchema]