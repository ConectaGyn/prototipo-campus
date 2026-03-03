"""
test_01_points.py

Testes E2E institucionais para o recurso /points do ClimaGyn.

Validações (profundas):
- Endpoint responde (status/tempo)
- Payload é lista não vazia
- Estrutura completa de cada Point (campos do modelo)
- Tipos corretos (str/int/float/bool/None)
- Faixas válidas de latitude/longitude
- Regras mínimas: id/name não vazios, influence_radius_m > 0
- Campos de auditoria em formato ISO datetime
- município: municipality_id pode ser None ou int válido
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

import pytest

from backend.app.tests.utils.http_client import APIClient


# ============================================================
# HELPERS DE LOG
# ============================================================

def _header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _fail(msg: str) -> None:
    raise AssertionError(msg)


# ============================================================
# HELPERS DE VALIDAÇÃO
# ============================================================

ISO_DATETIME_REGEX = re.compile(
    # Aceita "2026-02-19T02:37:19.690" e "2026-02-19T02:37:19.690Z"
    # e também com offset: "+00:00"
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(\.\d+)?"
    r"(Z|[+-]\d{2}:\d{2})?$"
)


def _is_iso_datetime(value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    return bool(ISO_DATETIME_REGEX.match(value))


def _require_keys(obj: Dict[str, Any], keys: List[str], idx: int) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        _fail(
            f"\n[POINT STRUCT ERROR]\n"
            f"Index: {idx}\n"
            f"Campos ausentes: {missing}\n"
            f"Objeto recebido (parcial): {str(obj)[:500]}"
        )


def _assert_type(field: str, value: Any, expected, idx: int) -> None:
    if not isinstance(value, expected):
        _fail(
            f"\n[POINT TYPE ERROR]\n"
            f"Index: {idx}\n"
            f"Campo: {field}\n"
            f"Esperado: {expected}\n"
            f"Recebido: {type(value)}\n"
            f"Valor: {value!r}"
        )


def _assert_optional_type(field: str, value: Any, expected, idx: int) -> None:
    if value is None:
        return
    _assert_type(field, value, expected, idx)


def _assert_float_range(field: str, value: float, lo: float, hi: float, idx: int) -> None:
    if not (lo <= value <= hi):
        _fail(
            f"\n[POINT RANGE ERROR]\n"
            f"Index: {idx}\n"
            f"Campo: {field}\n"
            f"Faixa esperada: [{lo}, {hi}]\n"
            f"Recebido: {value}"
        )


# ============================================================
# FIXTURE DO CLIENTE (usa nosso APIClient, não requests puro)
# ============================================================

@pytest.fixture(scope="session")
def api() -> APIClient:
    client = APIClient(verbose=True)
    print("\n" + "=" * 80)
    print("CLIENTE HTTP E2E INICIALIZADO (POINTS TEST)")
    print(f"BASE URL: {client.base_url}")
    print("=" * 80)
    return client


# ============================================================
# TESTES
# ============================================================

def test_points_endpoint_status_and_non_empty(api: APIClient) -> None:
    _header("SANIDADE DO ENDPOINT - /POINTS")

    resp = api.get("/points")
    resp.assert_status(200)

    payload = resp.json()
    if not isinstance(payload, list):
        _fail(
            f"\n[POINTS RESPONSE ERROR]\n"
            f"Esperado lista.\n"
            f"Recebido: {type(payload)}\n"
            f"Body: {str(payload)[:500]}"
        )

    total = len(payload)
    print(f"[POINTS] Total retornado: {total}")

    if total <= 0:
        _fail("[POINTS] Lista vazia. Esperado pelo menos 1 ponto.")

    if total < 10:
        _fail(
            f"[POINTS] Poucos pontos retornados ({total}). "
            f"Esperado pelo menos 10 para ambiente seedado."
        )

    print("[POINTS] Endpoint respondeu corretamente com lista não vazia.")


def test_points_payload_deep_validation(api: APIClient) -> None:
    _header("VALIDAÇÃO PROFUNDA DO PAYLOAD - /POINTS")

    resp = api.get("/points")
    resp.assert_status(200)
    points = resp.json()

    assert isinstance(points, list)
    assert len(points) > 0

    required_keys = [
        "id",
        "name",
        "municipality_id",
        "latitude",
        "longitude",
        "active",
        "influence_radius_m",
        "neighborhood",
        "description",
        "created_at",
        "updated_at",
    ]

    print(f"[POINTS] Validando {len(points)} ponto(s) com checagens profundas...")

    invalid_count = 0

    for idx, p in enumerate(points):
        try:
            if not isinstance(p, dict):
                _fail(
                    f"\n[POINT ITEM ERROR]\n"
                    f"Index: {idx}\n"
                    f"Esperado dict.\n"
                    f"Recebido: {type(p)}\n"
                    f"Valor: {p!r}"
                )

            _require_keys(p, required_keys, idx)

            _assert_type("id", p["id"], str, idx)
            _assert_type("name", p["name"], str, idx)

            if not p["id"].strip():
                _fail(f"\n[POINT VALUE ERROR]\nIndex: {idx}\nCampo: id\nMotivo: vazio")

            if not p["name"].strip():
                _fail(f"\n[POINT VALUE ERROR]\nIndex: {idx}\nCampo: name\nMotivo: vazio")

            mid = p["municipality_id"]
            if mid is not None:
                _assert_type("municipality_id", mid, int, idx)
                if mid <= 0:
                    _fail(
                        f"\n[POINT VALUE ERROR]\n"
                        f"Index: {idx}\n"
                        f"Campo: municipality_id\n"
                        f"Motivo: int inválido (<=0)\n"
                        f"Valor: {mid}"
                    )

            _assert_type("latitude", p["latitude"], (float, int), idx)
            _assert_type("longitude", p["longitude"], (float, int), idx)

            lat = float(p["latitude"])
            lon = float(p["longitude"])

            _assert_float_range("latitude", lat, -90.0, 90.0, idx)
            _assert_float_range("longitude", lon, -180.0, 180.0, idx)

            _assert_type("active", p["active"], bool, idx)

            _assert_type("influence_radius_m", p["influence_radius_m"], int, idx)
            if p["influence_radius_m"] <= 0:
                _fail(
                    f"\n[POINT VALUE ERROR]\n"
                    f"Index: {idx}\n"
                    f"Campo: influence_radius_m\n"
                    f"Motivo: deve ser > 0\n"
                    f"Valor: {p['influence_radius_m']}"
                )

            _assert_optional_type("neighborhood", p["neighborhood"], str, idx)
            _assert_optional_type("description", p["description"], str, idx)

            if not _is_iso_datetime(p["created_at"]):
                _fail(
                    f"\n[POINT DATETIME ERROR]\n"
                    f"Index: {idx}\n"
                    f"Campo: created_at\n"
                    f"Valor: {p['created_at']!r}\n"
                    f"Motivo: não está em ISO datetime"
                )

            if not _is_iso_datetime(p["updated_at"]):
                _fail(
                    f"\n[POINT DATETIME ERROR]\n"
                    f"Index: {idx}\n"
                    f"Campo: updated_at\n"
                    f"Valor: {p['updated_at']!r}\n"
                    f"Motivo: não está em ISO datetime"
                )

        except AssertionError:
            invalid_count += 1
            raise  

    print("[POINTS] Payload validado com sucesso (estrutura + tipagem + integridade).")
    print(f"[POINTS] Pontos inválidos detectados: {invalid_count}")


def test_points_performance_smoke(api: APIClient) -> None:
    _header("PERFORMANCE SMOKE - /POINTS")

    start = time.perf_counter()
    resp = api.get("/points")
    resp.assert_status(200)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    limit_ms = 5000.0
    print(f"[POINTS] Tempo: {elapsed_ms:.2f} ms | Limite: {limit_ms:.0f} ms")

    if elapsed_ms > limit_ms:
        _fail(
            f"\n[PERFORMANCE ERROR]\n"
            f"/points demorou demais.\n"
            f"Tempo: {elapsed_ms:.2f} ms\n"
            f"Limite: {limit_ms:.0f} ms\n"
            f"Dica: checar query no endpoint, eager loading, indexes."
        )

    print("[POINTS] Performance aceitável para ambiente atual.")
