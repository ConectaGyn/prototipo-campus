"""
test_04_municipalities.py

Valida entidade administrativa Municipality.

Testa:
- Estrutura da listagem
- CRUD completo isolado
- Estrutura do GeoJSON
- Performance
"""

import time
from datetime import datetime
from uuid import uuid4

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
# VALIDAÇÃO ESTRUTURAL
# ============================================================

def _validate_bbox(bbox: dict):
    required = ["min_lat", "min_lon", "max_lat", "max_lon"]
    missing = [k for k in required if k not in bbox]
    if missing:
        _fail(f"Campos ausentes no bbox: {missing}")

    if not (-90 <= bbox["min_lat"] <= 90):
        _fail("min_lat inválido")

    if not (-90 <= bbox["max_lat"] <= 90):
        _fail("max_lat inválido")

    if not (-180 <= bbox["min_lon"] <= 180):
        _fail("min_lon inválido")

    if not (-180 <= bbox["max_lon"] <= 180):
        _fail("max_lon inválido")

    if bbox["min_lat"] > bbox["max_lat"]:
        _fail("bbox inválido: min_lat > max_lat")

    if bbox["min_lon"] > bbox["max_lon"]:
        _fail("bbox inválido: min_lon > max_lon")


def _validate_municipality_structure(m: dict):
    required = [
        "id",
        "name",
        "ibge_code",
        "active",
        "bbox",
        "created_at",
    ]

    missing = [k for k in required if k not in m]
    if missing:
        _fail(f"Campos ausentes: {missing}\nPayload: {m}")

    if not isinstance(m["id"], int):
        _fail("id deve ser inteiro")

    if not isinstance(m["name"], str) or not m["name"].strip():
        _fail("name inválido")

    if not isinstance(m["ibge_code"], str) or not m["ibge_code"].isdigit():
        _fail("ibge_code inválido")

    if not isinstance(m["active"], bool):
        _fail("active deve ser booleano")

    _validate_bbox(m["bbox"])

    try:
        datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
    except Exception:
        _fail("created_at inválido")


# ============================================================
# TESTE 1 — LIST STRUCTURE
# ============================================================

def test_municipalities_list_structure(http_client: APIClient):
    _header("MUNICIPALITIES - LIST STRUCTURE")

    resp = http_client.get("/municipalities")
    resp.assert_status(200)

    data = resp.json()

    if not isinstance(data, list):
        _fail("Resposta de /municipalities deve ser lista")

    print(f"[MUNIC] Total retornado: {len(data)}")

    if not data:
        pytest.exit("Nenhum município retornado.")

    for m in data:
        _validate_municipality_structure(m)

    print("[MUNIC] Estrutura validada com sucesso.")


# ============================================================
# TESTE 2 — CRUD FLOW COMPLETO
# ============================================================

def test_municipality_crud_flow(http_client: APIClient):
    _header("MUNICIPALITIES - CRUD FLOW")

    unique_name = f"Testopolis_E2E_{uuid4().hex[:8]}"

    geo = http_client.get("/municipalities/1/geojson")
    geo.assert_status(200)
    geojson_real = geo.json()

    payload = {
        "name": unique_name,
        "ibge_code": "9999999",
        "active": True,
        "geojson": geojson_real,
    }

    # CREATE
    resp_create = http_client.post("/municipalities", json_body=payload)
    if resp_create.status_code not in (200, 201):
        _fail(f"Falha ao criar município: {resp_create.status_code}" f"{resp_create.raw.text[:500]}")

    created_data = resp_create.json()
    created_id = created_data["id"]
    print(f"[MUNIC] Criado ID: {created_id}")

    # READ
    resp_get = http_client.get(f"/municipalities/{created_id}")
    resp_get.assert_status(200)
    created_data = resp_get.json()

    _validate_municipality_structure(created_data)

    if created_data["name"] != unique_name:
        _fail("Nome não persistiu corretamente")

    # UPDATE
    resp_patch = http_client.patch(
        f"/municipalities/{created_id}",
        json_body={"active": False}
    )
    resp_patch.assert_status(200)

    resp_get_updated = http_client.get(f"/municipalities/{created_id}")
    resp_get_updated.assert_status(200)

    if resp_get_updated.json()["active"] is not False:
        _fail("PATCH não atualizou active corretamente")

    print("[MUNIC] Atualização validada.")

    # DELETE
    resp_delete = http_client.delete(f"/municipalities/{created_id}")
    resp_delete.assert_status(200)

    resp_after_delete = http_client.get(f"/municipalities/{created_id}")
    resp_delete.assert_status(200)

    deleted_data = resp_after_delete.json()

    if deleted_data["active"] is not False:
        _fail("DELETE não removeu município corretamente")

    print("[MUNIC] Remoção validada.")


# ============================================================
# TESTE 3 — GEOJSON
# ============================================================

def test_municipality_geojson_structure(http_client: APIClient):
    _header("MUNICIPALITIES - GEOJSON")

    resp_list = http_client.get("/municipalities")
    resp_list.assert_status(200)

    municipalities = resp_list.json()
    municipality_id = municipalities[0]["id"]

    resp_geo = http_client.get(f"/municipalities/{municipality_id}/geojson")
    resp_geo.assert_status(200)

    geo = resp_geo.json()

    if geo.get("type") != "FeatureCollection":
        _fail("GeoJSON type deve ser FeatureCollection")

    if "features" not in geo or not isinstance(geo["features"], list):
        _fail("GeoJSON inválido: features ausente ou inválido")

    print("[MUNIC] GeoJSON validado.")


# ============================================================
# TESTE 4 — PERFORMANCE
# ============================================================

def test_municipalities_performance(http_client: APIClient):
    _header("MUNICIPALITIES - PERFORMANCE")

    start = time.perf_counter()
    resp = http_client.get("/municipalities")
    elapsed = (time.perf_counter() - start) * 1000

    resp.assert_status(200)

    print(f"[MUNIC] Tempo total: {elapsed:.2f} ms")

    assert elapsed < 6000, "GET /municipalities demorou mais de 6s"
