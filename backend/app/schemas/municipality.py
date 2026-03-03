"""
schemas/municipality.py

Contratos públicos da API relacionados a Municípios monitorados.

Responsabilidade:
- Validar entrada/saída da API para Municipality
- Validar GeoJSON de forma leve (sem bibliotecas externas)
- Não conter lógica de negócio (ex: cálculo de bbox)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


# =====================================================
# GEOJSON - VALIDADORES LEVES
# =====================================================

_ALLOWED_GEOMETRY_TYPES = {"Polygon", "MultiPolygon"}
_ALLOWED_TOPLEVEL_TYPES = {"Feature", "FeatureCollection", "Polygon", "MultiPolygon"}


def _is_non_empty_coordinates(value: Any) -> bool:
    """
    Verifica se `coordinates` tem estrutura não vazia.
    Não valida geometria completamente (isso exigiria libs),
    mas impede payloads claramente inválidos.
    """
    if value is None:
        return False
    if not isinstance(value, list):
        return False
    if len(value) == 0:
        return False
    return True


def _validate_geojson_minimal(geojson: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validação minimalista e robusta de GeoJSON.

    Aceita:
        - Feature { type, geometry{type, coordinates} }
        - FeatureCollection { type, features[] }
        - Geometry direta { type: Polygon|MultiPolygon, coordinates }

    Não realiza validação topológica completa,
    """

    if not isinstance(geojson, dict):
        raise ValueError("geojson deve ser um objeto JSON (dict).")

    gtype = geojson.get("type")
    if not isinstance(gtype, str):
        raise ValueError("geojson.type é obrigatório e deve ser string.")

    # CASO 1 — FEATURE
    if gtype == "Feature":
        geometry = geojson.get("geometry")
        if not isinstance(geometry, dict):
            raise ValueError("geojson Feature deve conter 'geometry' como objeto.")

        geom_type = geometry.get("type")
        if geom_type not in _ALLOWED_GEOMETRY_TYPES:
            raise ValueError(
                f"geojson.geometry.type inválido: {geom_type}. "
                f"Permitidos: {sorted(_ALLOWED_GEOMETRY_TYPES)}"
            )

        coords = geometry.get("coordinates")
        if not _is_non_empty_coordinates(coords):
            raise ValueError("geojson.geometry.coordinates deve ser lista não vazia.")

        return geojson

    # CASO 2 — FEATURE COLLECTION
    if gtype == "FeatureCollection":
        features = geojson.get("features")

        if not isinstance(features, list) or len(features) == 0:
            raise ValueError("geojson FeatureCollection deve conter 'features' como lista não vazia.")

        for i, feature in enumerate(features):

            if not isinstance(feature, dict):
                raise ValueError(f"geojson.features[{i}] deve ser um objeto.")

            if feature.get("type") != "Feature":
                raise ValueError(f"geojson.features[{i}].type deve ser 'Feature'.")

            geometry = feature.get("geometry")
            if not isinstance(geometry, dict):
                raise ValueError(f"geojson.features[{i}].geometry deve ser objeto.")

            geom_type = geometry.get("type")
            if geom_type not in _ALLOWED_GEOMETRY_TYPES:
                raise ValueError(
                    f"geojson.features[{i}].geometry.type inválido: {geom_type}. "
                    f"Permitidos: {sorted(_ALLOWED_GEOMETRY_TYPES)}"
                )

            coords = geometry.get("coordinates")
            if not _is_non_empty_coordinates(coords):
                raise ValueError(
                    f"geojson.features[{i}].geometry.coordinates deve ser lista não vazia."
                )

        return geojson

    # CASO 3 — GEOMETRIA DIRETA (Polygon / MultiPolygon)
    if gtype in _ALLOWED_GEOMETRY_TYPES:

        coords = geojson.get("coordinates")
        if not _is_non_empty_coordinates(coords):
            raise ValueError("geojson.coordinates deve ser lista não vazia.")

        return geojson

    # TIPO NÃO SUPORTADO
    raise ValueError(
        f"geojson.type inválido: {gtype}. "
        f"Permitidos: ['Feature', 'FeatureCollection', 'Polygon', 'MultiPolygon']"
    )


# =====================================================
# BBOX
# =====================================================

class MunicipalityBBoxSchema(BaseModel):
    """
    Bounding box (WGS84) para facilitar grid e viewport do frontend.
    """
    min_lat: float = Field(..., description="Latitude mínima (sul)")
    min_lon: float = Field(..., description="Longitude mínima (oeste)")
    max_lat: float = Field(..., description="Latitude máxima (norte)")
    max_lon: float = Field(..., description="Longitude máxima (leste)")


# =====================================================
# SCHEMAS BASE
# =====================================================

class MunicipalityBaseSchema(BaseModel):
    """
    Campos estruturais do município.
    """
    name: str = Field(..., min_length=2, max_length=120, description="Nome do município")
    ibge_code: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Código IBGE (opcional)",
    )

    active: bool = Field(
        default=True,
        description="Indica se o município está ativo para monitoramento (soft delete via active=False)",
    )

    geojson: Dict[str, Any] = Field(
        ...,
        description="GeoJSON do município (Feature Polygon/MultiPolygon ou Geometry Polygon/MultiPolygon)",
    )

    @field_validator("geojson")
    @classmethod
    def validate_geojson(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return _validate_geojson_minimal(v)


# =====================================================
# SCHEMAS DE ENTRADA
# =====================================================

class MunicipalityCreateSchema(MunicipalityBaseSchema):
    """
    Schema para criação de municípios.
    Endpoint tipicamente protegido (admin).
    """
    pass


class MunicipalityUpdateSchema(BaseModel):
    """
    Schema para atualização parcial.
    Todos os campos opcionais.
    """
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    ibge_code: Optional[str] = Field(default=None, max_length=10)
    active: Optional[bool] = None
    geojson: Optional[Dict[str, Any]] = None

    @field_validator("geojson")
    @classmethod
    def validate_geojson(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return None
        return _validate_geojson_minimal(v)


# =====================================================
# SCHEMAS DE SAÍDA
# =====================================================

class MunicipalityResponseSchema(BaseModel):
    """
    Representação pública do município.
    """
    id: int = Field(..., description="ID interno do município")
    name: str = Field(..., description="Nome do município")
    ibge_code: Optional[str] = Field(default=None, description="Código IBGE (opcional)")
    active: bool = Field(..., description="Indica se o município está ativo")

    geojson: Dict[str, Any] = Field(
        ...,
        description="GeoJSON do município (híbrido: pode ter sido enviado no POST ou lido do arquivo local e persistido no banco)",
    )

    bbox: MunicipalityBBoxSchema = Field(
        ...,
        description="Bounding box do município (WGS84), útil para grid e viewport",
    )

    created_at: datetime = Field(..., description="Timestamp de criação")
    updated_at: datetime = Field(..., description="Timestamp de atualização")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, m: Any) -> "MunicipalityResponseSchema":
        """
        Constrói resposta a partir do model ORM Municipality.

        Espera que o model tenha:
        - bbox_min_lat, bbox_min_lon, bbox_max_lat, bbox_max_lon
        """
        return cls(
            id=int(m.id),
            name=str(m.name),
            ibge_code=(str(m.ibge_code) if m.ibge_code is not None else None),
            active=bool(m.active),
            geojson=dict(m.geojson),
            bbox=MunicipalityBBoxSchema(
                min_lat=float(m.bbox_min_lat),
                min_lon=float(m.bbox_min_lon),
                max_lat=float(m.bbox_max_lat),
                max_lon=float(m.bbox_max_lon),
            ),
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


class MunicipalitySimpleSchema(BaseModel):
    """
    Versão leve (ex: dropdown no frontend, seleção rápida).
    """
    id: int
    name: str
    ibge_code: Optional[str] = None
    active: bool

    model_config = ConfigDict(from_attributes=True)
