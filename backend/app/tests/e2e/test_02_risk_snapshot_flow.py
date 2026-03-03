"""
test_02_risk_snapshot_flow.py

Valida o fluxo completo de snapshot de risco por ponto.

Testa:
- Compute inicial
- Cache hit
- compute_only
- cache_only
- Estrutura profunda do payload
- Consistência temporal
- Performance básica

Executado contra backend real.
"""

import time
import urllib.parse
from datetime import datetime, timedelta, timezone

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


def _validate_snapshot_structure(data: dict):
    required_keys = [
        "point_id",
        "icra",
        "icra_std",
        "nivel_risco",
        "confianca",
        "referencia_em",
        "fonte",
    ]

    missing = [k for k in required_keys if k not in data]
    if missing:
        _fail(
            f"\n[SNAPSHOT STRUCT ERROR]\n"
            f"Campos ausentes: {missing}\n"
            f"Payload parcial: {data}"
        )

    # ----------------------------
    # Valida tipos
    # ----------------------------

    if not isinstance(data["point_id"], str):
        _fail("point_id deve ser string")

    if not isinstance(data["icra"], (int, float)):
        _fail("icra deve ser numérico")

    if not (0 <= data["icra"] <= 1):
        _fail(f"icra fora do intervalo [0,1]: {data['icra']}")

    valid_levels = {"Baixo", "Moderado", "Alto", "Muito Alto"}
    if data["nivel_risco"] not in valid_levels:
        _fail(
            f"nivel_risco inválido: {data['nivel_risco']}\n"
            f"Esperado um de: {valid_levels}"
        )

    valid_confidence = {"Alta", "Média", "Baixa"}
    if data["confianca"] not in valid_confidence:
        _fail(
            f"confianca inválida: {data['confianca']}\n"
            f"Esperado um de: {valid_confidence}"
        )

    try:
        datetime.fromisoformat(data["referencia_em"])
    except Exception:
        _fail("referencia_em não é datetime ISO válido")


def _get_valid_point_id(http_client: APIClient) -> str:
    resp = http_client.get("/points")
    resp.assert_status(200)
    points = resp.json()

    if not points:
        pytest.exit("Nenhum ponto disponível para teste.")

    return points[0]["id"]


# ============================================================
# TESTE 1 — COMPUTE INICIAL
# ============================================================

def test_snapshot_initial_compute(http_client: APIClient):
    _header("SNAPSHOT FLOW - PRIMEIRA EXECUÇÃO")

    point_id = _get_valid_point_id(http_client)

    start = time.perf_counter()
    resp = http_client.get(f"/points/{point_id}/risk")
    elapsed = (time.perf_counter() - start) * 1000

    resp.assert_status(200)
    data = resp.json()

    print(f"[SNAPSHOT] Tempo compute inicial: {elapsed:.2f} ms")

    _validate_snapshot_structure(data)

    print("[SNAPSHOT] Compute inicial válido.")


# ============================================================
# TESTE 2 — CACHE HIT
# ============================================================

def test_snapshot_cache_hit(http_client: APIClient):
    _header("SNAPSHOT FLOW - CACHE HIT")

    point_id = _get_valid_point_id(http_client)

    first = http_client.get(f"/points/{point_id}/risk")
    first.assert_status(200)
    first_data = first.json()

    start = time.perf_counter()
    second = http_client.get(f"/points/{point_id}/risk")
    elapsed = (time.perf_counter() - start) * 1000

    second.assert_status(200)
    second_data = second.json()

    print(f"[SNAPSHOT] Tempo cache hit: {elapsed:.2f} ms")

    if first_data["referencia_em"] != second_data["referencia_em"]:
        _fail("Cache não reutilizou snapshot (referencia_em diferente)")

    print("[SNAPSHOT] Cache reutilizado corretamente.")


# ============================================================
# TESTE 3 — COMPUTE ONLY
# ============================================================

def test_snapshot_compute_only(http_client: APIClient):
    _header("SNAPSHOT FLOW - COMPUTE ONLY")

    point_id = _get_valid_point_id(http_client)

    resp = http_client.get(f"/points/{point_id}/risk?source=compute_only")
    resp.assert_status(200)

    data = resp.json()

    _validate_snapshot_structure(data)

    print("[SNAPSHOT] compute_only executado com sucesso.")


# ============================================================
# TESTE 4 — CACHE ONLY SEM SNAPSHOT
# ============================================================

def test_snapshot_cache_only_without_existing(http_client: APIClient):
    _header("SNAPSHOT FLOW - CACHE ONLY SEM SNAPSHOT")

    point_id = _get_valid_point_id(http_client)

    future_ts_raw = (datetime.now(timezone.utc)+timedelta(days=30)).isoformat()
    future_ts = urllib.parse.quote(future_ts_raw)

    resp = http_client.get(
        f"/points/{point_id}/risk?source=cache_only&at={future_ts}"
    )

    if resp.status_code not in (204, 200):
        _fail(
            f"Status inesperado para cache_only: {resp.status_code}"
        )

    print("[SNAPSHOT] cache_only tratado corretamente.")


# ============================================================
# TESTE 5 — PERFORMANCE SMOKE
# ============================================================

def test_snapshot_performance_smoke(http_client: APIClient):
    _header("SNAPSHOT FLOW - PERFORMANCE SMOKE")

    point_id = _get_valid_point_id(http_client)

    start = time.perf_counter()
    resp = http_client.get(f"/points/{point_id}/risk")
    elapsed = (time.perf_counter() - start) * 1000

    resp.assert_status(200)

    print(f"[SNAPSHOT] Tempo total: {elapsed:.2f} ms")

    assert elapsed < 5000, "Snapshot demorou mais de 5s"
