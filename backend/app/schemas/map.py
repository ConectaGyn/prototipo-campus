"""
Schemas para endpoints de mapa e snapshot pontual.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MapPointViewSchema(BaseModel):
    id: str = Field(..., description="Identificador unico do ponto")
    nome: str = Field(..., description="Nome do ponto critico")

    latitude: float = Field(..., description="Latitude do ponto")
    longitude: float = Field(..., description="Longitude do ponto")

    bairro: Optional[str] = Field(None, description="Bairro ou regiao do ponto")
    raio_influencia_m: int = Field(..., description="Raio de influencia em metros")
    ativo: bool = Field(..., description="Indica se o ponto esta ativo")
    municipality_id: Optional[int] = Field(
        None, description="ID do municipio ao qual o ponto pertence"
    )

    icra: Optional[float] = Field(
        None, ge=0, le=1, description="Indice Climatico de Risco de Alagamento (0 a 1)"
    )
    icra_std: Optional[float] = Field(
        None, description="Desvio padrao do ICRA (incerteza do modelo)"
    )
    nivel_risco: Optional[str] = Field(
        None, description="Classificacao absoluta retornada pelo modelo"
    )
    nivel_risco_relativo: Optional[str] = Field(
        None, description="Classificacao relativa no ciclo (quartis)"
    )
    confianca: Optional[str] = Field(
        None, description="Nivel de confianca da inferencia"
    )
    referencia_em: Optional[datetime] = Field(
        None, description="Timestamp de referencia do snapshot utilizado"
    )


class RiskSnapshotResponse(BaseModel):
    point_id: str = Field(..., description="Identificador unico do ponto critico")

    icra: float = Field(
        ..., ge=0, le=1, description="Indice Climatico de Risco de Alagamento (0 a 1)"
    )
    icra_std: float = Field(..., description="Desvio padrao do ICRA")

    nivel_risco: str = Field(
        ..., description="Classificacao absoluta retornada pelo modelo"
    )
    nivel_risco_relativo: Optional[str] = Field(
        None, description="Classificacao relativa no ciclo (quartis)"
    )
    confianca: str = Field(..., description="Nivel de confianca da inferencia")

    referencia_em: datetime = Field(
        ..., description="Timestamp exato do snapshot utilizado"
    )
    fonte: str = Field(
        ...,
        description="'snapshot' (persistido) ou 'on_demand' (calculado sob demanda)",
        json_schema_extra={"example": "snapshot"},
    )

    @classmethod
    def from_model(cls, snapshot, source: str, relative_level: Optional[str] = None):
        return cls(
            point_id=snapshot.point_id,
            icra=snapshot.icra,
            icra_std=snapshot.icra_std,
            nivel_risco=snapshot.nivel_risco,
            nivel_risco_relativo=relative_level,
            confianca=snapshot.confianca,
            referencia_em=snapshot.snapshot_timestamp,
            fonte=source,
        )


class MapPointsResponse(BaseModel):
    pontos: List[MapPointViewSchema] = Field(
        ..., description="Lista de pontos criticos com snapshot de risco"
    )
    snapshot_timestamp: Optional[datetime] = Field(
        None, description="Timestamp exato do snapshot usado na resposta"
    )
    snapshot_valid_until: Optional[datetime] = Field(
        None, description="Momento em que o snapshot deixa de ser considerado valido"
    )
    total: int = Field(..., description="Quantidade total de pontos retornados")
