"""
test_03_map_state.py

Valida o estado agregado do mapa de risco.

Este teste reconhece dois estados válidos do domínio:

1. Ponto ainda não avaliado (snapshot inexistente)
2. Ponto avaliado (snapshot completo e consistente)

Testa:
- Estrutura do envelope
- Estrutura profunda de cada ponto
- Coerência de estado (snapshot inexistente vs existente)
- Consistência com endpoint individual
- Performance
"""

import time
from datetime import datetime

import pytest

from backend.app.tests.utils.http_client import APIClient


# ============================================================
# UTILITÁRIOS
# ============================================================

def _header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _fail(msg: str):
    raise AssertionError(msg)


# ============================================================
# VALIDAÇÃO DE PONTO
# ============================================================

def _validate_point_structure(point: dict):
    required_keys = [
        "id",
        "nome",
        "latitude",
        "longitude",
        "bairro",
        "raio_influencia_m",
        "ativo",
        "municipality_id",
        "icra",
        "icra_std",
        "nivel_risco",
        "confianca",
        "referencia_em",
    ]

    missing = [k for k in required_keys if k not in point]
    if missing:
        _fail(
            f"\n[MAP POINT STRUCT ERROR]\n"
            f"Campos ausentes: {missing}\n"
            f"Ponto: {point}"
        )

    # ----------------------------
    # Validação básica estrutural
    # ----------------------------

    if not isinstance(point["id"], str):
        _fail("id deve ser string")

    if not isinstance(point["latitude"], (int, float)) or not (-90 <= point["latitude"] <= 90):
        _fail(f"Latitude inválida: {point['latitude']}")

    if not isinstance(point["longitude"], (int, float)) or not (-180 <= point["longitude"] <= 180):
        _fail(f"Longitude inválida: {point['longitude']}")

    # -------------------------------------------------
    # VALIDAÇÃO DE ESTADO DE SNAPSHOT
    # -------------------------------------------------

    snapshot_fields = [
        point.get("icra"),
        point.get("nivel_risco"),
        point.get("confianca"),
        point.get("referencia_em"),
    ]

    # Caso 1 — Snapshot inexistente (estado válido)
    if all(field is None for field in snapshot_fields):
        return

    if any(field is None for field in snapshot_fields):
        _fail(
            "Estado inconsistente: snapshot parcialmente preenchido.\n"
            f"Ponto: {point}"
        )

    # Caso 2 — Snapshot existente → validar profundamente

    if not isinstance(point["icra"], (int, float)) or not (0 <= point["icra"] <= 1):
        _fail(f"icra fora do intervalo [0,1]: {point['icra']}")

    if not isinstance(point["icra_std"], (int, float)):
        _fail("icra_std deve ser numérico")

    valid_levels = {"Baixo", "Moderado", "Alto", "Muito Alto"}
    if point["nivel_risco"] not in valid_levels:
        _fail(
            f"nivel_risco inválido: {point['nivel_risco']}\n"
            f"Esperado um de: {valid_levels}"
        )

    valid_confidence = {"Alta", "Média", "Baixa"}
    if point["confianca"] not in valid_confidence:
        _fail(
            f"confianca inválida: {point['confianca']}\n"
            f"Esperado um de: {valid_confidence}"
        )

    try:
        datetime.fromisoformat(point["referencia_em"].replace("Z", "+00:00"))
    except Exception:
        _fail(f"referencia_em inválido: {point['referencia_em']}")


# ============================================================
# VALIDAÇÃO DO ENVELOPE
# ============================================================

def _validate_envelope_structure(payload: dict):
    required_keys = [
        "pontos",
        "snapshot_timestamp",
        "snapshot_valid_until",
        "total",
    ]

    missing = [k for k in required_keys if k not in payload]
    if missing:
        _fail(
            f"\n[MAP ENVELOPE ERROR]\n"
            f"Campos ausentes: {missing}\n"
            f"Payload: {payload}"
        )

    if not isinstance(payload["pontos"], list):
        _fail("pontos deve ser lista")

    if payload["total"] != len(payload["pontos"]):
        _fail(
            f"Inconsistência em total: total={payload['total']} "
            f"len(pontos)={len(payload['pontos'])}"
        )

    try:
        datetime.fromisoformat(payload["snapshot_timestamp"].replace("Z", "+00:00"))
        datetime.fromisoformat(payload["snapshot_valid_until"].replace("Z", "+00:00"))
    except Exception:
        _fail("snapshot_timestamp ou snapshot_valid_until inválido")


# ============================================================
# TESTE 1 — ESTRUTURA DO MAPA
# ============================================================

def test_map_state_structure(http_client: APIClient):
    _header("MAP STATE - ESTRUTURA")

    resp = http_client.get("/map/points")
    resp.assert_status(200)

    payload = resp.json()

    _validate_envelope_structure(payload)

    pontos = payload["pontos"]

    if not pontos:
        pytest.exit("Nenhum ponto retornado no mapa.")

    print(f"[MAP] Total de pontos retornados: {len(pontos)}")

    evaluated = 0
    not_evaluated = 0

    for point in pontos:
        _validate_point_structure(point)

        if point["icra"] is None:
            not_evaluated += 1
        else:
            evaluated += 1

    print(f"[MAP] Pontos avaliados: {evaluated}")
    print(f"[MAP] Pontos não avaliados: {not_evaluated}")
    print("[MAP] Estrutura validada com sucesso.")


# ============================================================
# TESTE 2 — CONSISTÊNCIA COM SNAPSHOT INDIVIDUAL
# ============================================================

def test_map_state_consistency_with_point(http_client: APIClient):
    _header("MAP STATE - CONSISTÊNCIA COM SNAPSHOT INDIVIDUAL")

    resp = http_client.get("/map/points")
    resp.assert_status(200)
    payload = resp.json()

    pontos = payload["pontos"]

    evaluated_points = [p for p in pontos if p["icra"] is not None]

    if not evaluated_points:
        pytest.skip("Nenhum ponto avaliado disponível para teste de consistência.")

    sample_point = evaluated_points[0]
    point_id = sample_point["id"]

    resp_individual = http_client.get(f"/points/{point_id}/risk")
    resp_individual.assert_status(200)

    individual_data = resp_individual.json()

    if sample_point["icra"] != individual_data["icra"]:
        _fail("Inconsistência entre icra do mapa e snapshot individual")

    if sample_point["nivel_risco"] != individual_data["nivel_risco"]:
        _fail("Inconsistência entre nivel_risco do mapa e snapshot individual")

    if sample_point["referencia_em"] != individual_data["referencia_em"]:
        _fail("Inconsistência entre referencia_em do mapa e snapshot individual")

    print("[MAP] Consistência validada com snapshot individual.")


# ============================================================
# TESTE 3 — PERFORMANCE
# ============================================================

def test_map_state_performance(http_client: APIClient):
    _header("MAP STATE - PERFORMANCE")

    start = time.perf_counter()
    resp = http_client.get("/map/points")
    elapsed = (time.perf_counter() - start) * 1000

    resp.assert_status(200)

    print(f"[MAP] Tempo total: {elapsed:.2f} ms")

    assert elapsed < 8000, "Map state demorou mais de 8s"
