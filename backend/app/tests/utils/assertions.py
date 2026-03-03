"""
utils/assertions.py

Camada central de validação para testes E2E.

Objetivos:
- Padronizar falhas
- Reduzir duplicação de lógica
- Garantir clareza nas mensagens
- Fornecer validações estruturais reutilizáveis

IMPORTANTE:
- Não contém lógica de negócio
- Não acessa banco
- Não depende de HTTP
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
import math


# ============================================================
# CORE
# ============================================================

def _fail(message: str) -> None:
    """
    Falha explícita padronizada.
    """
    raise AssertionError(f"\n[TEST FAILURE]\n{message}")


# ============================================================
# BASIC STRUCTURE
# ============================================================

def assert_field_exists(obj: Dict[str, Any], field: str) -> None:
    if field not in obj:
        _fail(f"Campo ausente: '{field}'")


def assert_type(value: Any, expected_type: type, field_name: str) -> None:
    if not isinstance(value, expected_type):
        _fail(
            f"Campo '{field_name}' deveria ser do tipo "
            f"{expected_type.__name__}, mas recebeu {type(value).__name__}"
        )


def assert_not_empty(value: Any, field_name: str) -> None:
    if not value:
        _fail(f"Campo '{field_name}' está vazio.")


def assert_equal(a: Any, b: Any, message: str = "") -> None:
    if a != b:
        _fail(message or f"Valores diferentes: {a} != {b}")


# ============================================================
# NUMERIC
# ============================================================

def assert_positive(value: float, field_name: str) -> None:
    if value <= 0:
        _fail(f"'{field_name}' deve ser positivo. Valor atual: {value}")


def assert_non_negative(value: float, field_name: str) -> None:
    if value < 0:
        _fail(f"'{field_name}' não pode ser negativo. Valor atual: {value}")


def assert_close(
    a: float,
    b: float,
    tolerance: float,
    message: str = ""
) -> None:
    if not math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance):
        _fail(
            message
            or f"Valores não são próximos dentro da tolerância {tolerance}: {a} vs {b}"
        )

# ============================================================
# TEMPORAL
# ============================================================

def assert_datetime_string(value: str, field_name: str) -> None:
    try:
        datetime.fromisoformat(value)
    except Exception:
        _fail(f"Campo '{field_name}' não é datetime ISO válido: {value}")


def assert_timestamp_changed(old: str, new: str) -> None:
    if old == new:
        _fail("Timestamp não mudou após recomputação.")


def assert_not_future(value: str, field_name: str) -> None:
    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        _fail(f"Campo '{field_name}' não é datetime ISO válido.")

    now = datetime.now(timezone.utc)

    if dt > now:
        _fail(f"'{field_name}' está no futuro: {value}")

# ============================================================
# GEOJSON
# ============================================================

def assert_geojson_feature_collection(obj: Dict[str, Any]) -> None:
    assert_field_exists(obj, "type")
    assert_equal(obj["type"], "FeatureCollection", "GeoJSON deve ser FeatureCollection.")

    assert_field_exists(obj, "features")
    assert_type(obj["features"], list, "features")

    if not obj["features"]:
        _fail("GeoJSON 'features' está vazio.")


def assert_geojson_feature(feature: Dict[str, Any]) -> None:
    assert_field_exists(feature, "type")
    assert_equal(feature["type"], "Feature", "Objeto deve ser Feature.")

    assert_field_exists(feature, "geometry")
    assert_field_exists(feature, "properties")

    geometry = feature["geometry"]
    assert_field_exists(geometry, "type")
    assert_equal(geometry["type"], "Polygon", "Geometry deve ser Polygon.")

    assert_field_exists(geometry, "coordinates")
    assert_type(geometry["coordinates"], list, "coordinates")

    properties = feature["properties"]
    assert_field_exists(properties, "risk_value")
    assert_field_exists(properties, "risk_level")
    assert_field_exists(properties, "grid_resolution_m")

    assert_non_negative(properties["risk_value"], "risk_value")

# ============================================================
# STATISTICS
# ============================================================

def assert_area_consistency(
    total_cells: int,
    resolution_m: int,
    total_area_m2: float,
) -> None:
    expected_area = total_cells * (resolution_m ** 2)
    assert_close(
        total_area_m2,
        expected_area,
        tolerance=1e-6,
        message=(
            f"Inconsistência de área: esperado {expected_area}, "
            f"mas recebido {total_area_m2}"
        ),
    )


def assert_percentage_valid(value: float, field_name: str) -> None:
    if not (0.0 <= value <= 1.0):
        _fail(f"'{field_name}' deve estar entre 0 e 1. Valor atual: {value}")


def assert_area_bounds(
    high_area: float,
    total_area: float,
) -> None:
    if high_area > total_area:
        _fail(
            f"Área de alto risco ({high_area}) maior que área total ({total_area})."
        )

# ============================================================
# PERFORMANCE
# ============================================================

def assert_performance_within(
    elapsed_ms: float,
    limit_ms: float,
    context: str = "",
) -> None:
    if elapsed_ms > limit_ms:
        _fail(
            f"{context} excedeu limite de performance: "
            f"{elapsed_ms:.2f}ms > {limit_ms:.2f}ms"
        )
