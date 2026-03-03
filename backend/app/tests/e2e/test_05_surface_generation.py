"""
E2E - Surface Generation

Valida completamente o módulo de geração de superfícies espaciais.

Escopo:
- Bucket real do banco
- Envelope completo
- Metadata
- Recompute forçado
- Consistência matemática
- Estrutura GeoJSON
- Performance
"""

import math
from datetime import datetime
from typing import Dict, Any

import pytest

from backend.app.tests.utils.http_client import APIClient
from backend.app.tests.utils.assertions import _fail
from backend.app.database import SessionLocal
from backend.app.repositories.risk_repository import RiskRepository


# ============================================================
# CONFIG
# ============================================================

MUNICIPALITY_ID = 1
MAX_ACCEPTABLE_MS = 5000  

# ============================================================
# HELPERS
# ============================================================

def _get_latest_bucket() -> datetime:
    db = SessionLocal()
    try:
        repo = RiskRepository(db)
        bucket = repo.get_latest_bucket_timestamp()
        return bucket
    finally:
        db.close()


# ============================================================
# BUCKET
# ============================================================

def test_surface_bucket_exists():
    print("\n" + "=" * 80)
    print("VALIDAÇÃO DO BUCKET")
    print("=" * 80)

    bucket = _get_latest_bucket()

    if not bucket:
        _fail("Nenhum snapshot disponível no sistema. Surface não pode ser gerada.")

    print(f"[BUCKET] Último bucket encontrado: {bucket.isoformat()}")
    assert isinstance(bucket, datetime)


# ============================================================
# ENVELOPE COMPLETO
# ============================================================

def test_surface_envelope_generation():
    print("\n" + "=" * 80)
    print("SURFACE - ENVELOPE COMPLETO")
    print("=" * 80)

    bucket = _get_latest_bucket()
    api = APIClient()

    resp = api.get(f"/surface/{MUNICIPALITY_ID}")
    resp.assert_status(200)

    data = resp.json()

    required_fields = [
        "municipality_id",
        "municipality_name",
        "reference_ts",
        "computed_at",
        "valid_until",
        "grid_resolution_m",
        "kernel_sigma_m",
        "stats",
        "geojson",
    ]

    for field in required_fields:
        if field not in data:
            _fail(f"Campo ausente no envelope: {field}")

    if data["municipality_id"] != MUNICIPALITY_ID:
        _fail("municipality_id incorreto no envelope.")

    if data["reference_ts"] != bucket.isoformat():
        _fail("reference_ts não corresponde ao bucket atual.")

    stats = data["stats"]

    total_cells = stats["total_cells"]
    grid_res = data["grid_resolution_m"]
    total_area = stats["total_area_m2"]

    if total_cells <= 0:
        _fail("Surface retornou zero células.")

    expected_area = total_cells * (grid_res ** 2)

    if not math.isclose(total_area, expected_area, rel_tol=0.0001):
        _fail("Área total inconsistente com grid_resolution_m.")

    print(f"[SURFACE] Total células: {total_cells}")
    print(f"[SURFACE] Área total: {total_area} m²")
    print(f"[SURFACE] High risk %: {stats['high_risk_percentage'] * 100:.2f}%")

    assert data["geojson"]["type"] == "FeatureCollection"
    assert len(data["geojson"]["features"]) > 0


# ============================================================
# METADATA
# ============================================================

def test_surface_metadata():
    print("\n" + "=" * 80)
    print("SURFACE - METADATA")
    print("=" * 80)

    api = APIClient()

    resp = api.get(f"/surface/{MUNICIPALITY_ID}/metadata")
    resp.assert_status(200)

    data = resp.json()

    if "geojson" in data:
        _fail("Metadata não deveria conter geojson.")

    required_fields = [
        "municipality_id",
        "reference_ts",
        "computed_at",
        "grid_resolution_m",
        "kernel_sigma_m",
        "stats",
    ]

    for field in required_fields:
        if field not in data:
            _fail(f"Campo ausente na metadata: {field}")

    print("[METADATA] Metadata validado com sucesso.")


# ============================================================
# RECOMPUTE FLOW
# ============================================================

def test_surface_recompute_flow():
    print("\n" + "=" * 80)
    print("SURFACE - RECOMPUTE FLOW")
    print("=" * 80)

    api = APIClient()

    resp_before = api.get(f"/surface/{MUNICIPALITY_ID}")
    resp_before.assert_status(200)
    before_data = resp_before.json()
    computed_before = before_data["computed_at"]

    resp_recompute = api.post(f"/surface/{MUNICIPALITY_ID}/recompute")
    resp_recompute.assert_status(200)

    resp_after = api.get(f"/surface/{MUNICIPALITY_ID}")
    resp_after.assert_status(200)
    after_data = resp_after.json()
    computed_after = after_data["computed_at"]

    print(f"[RECOMPUTE] Computed_at anterior: {computed_before}")
    print(f"[RECOMPUTE] Computed_at novo:     {computed_after}")

    if computed_before == computed_after:
        _fail("Recompute não alterou computed_at.")

    print("[RECOMPUTE] Recompute validado com sucesso.")


# ============================================================
# GEOJSON STRUCTURE
# ============================================================

def test_surface_geojson_structure():
    print("\n" + "=" * 80)
    print("SURFACE - GEOJSON STRUCTURE")
    print("=" * 80)

    api = APIClient()
    resp = api.get(f"/surface/{MUNICIPALITY_ID}")
    resp.assert_status(200)

    data = resp.json()
    geo = data["geojson"]

    if geo["type"] != "FeatureCollection":
        _fail("GeoJSON não é FeatureCollection.")

    features = geo["features"]

    if not isinstance(features, list) or not features:
        _fail("GeoJSON features inválido ou vazio.")

    for feature in features[:10]:
        if feature["type"] != "Feature":
            _fail("Feature inválida.")

        geom = feature["geometry"]
        props = feature["properties"]

        if geom["type"] != "Polygon":
            _fail("Geometria não é Polygon.")

        if not isinstance(geom["coordinates"], list):
            _fail("Coordinates inválido.")

        if "risk_value" not in props:
            _fail("risk_value ausente.")

        if "risk_level" not in props:
            _fail("risk_level ausente.")

    print("[GEOJSON] Estrutura validada (10 amostras).")


# ============================================================
# PERFORMANCE
# ============================================================

def test_surface_performance():
    print("\n" + "=" * 80)
    print("SURFACE - PERFORMANCE")
    print("=" * 80)

    api = APIClient()

    resp = api.get(f"/surface/{MUNICIPALITY_ID}")
    resp.assert_status(200)

    elapsed = resp.elapsed_ms

    print(f"[PERFORMANCE] Tempo: {elapsed:.2f} ms")

    if elapsed > MAX_ACCEPTABLE_MS:
        _fail(f"Surface demorou mais que o limite aceitável ({MAX_ACCEPTABLE_MS} ms).")

    print("[PERFORMANCE] Tempo dentro do aceitável.")
