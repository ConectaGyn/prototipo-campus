"""
test_00_health.py

Teste institucional de sanidade do Backend Core do ClimaGyn.

Objetivo:
- Validar que a API está no ar
- Validar que o contrato básico do root está correto
- Validar que o healthcheck responde corretamente
- Garantir tempo de resposta aceitável

IMPORTANTE:
Se este teste falhar, os demais testes não são confiáveis.
"""

import time
import pytest


# ============================================================
# SANIDADE DO ROOT
# ============================================================

def test_root_endpoint(http_client):
    print("\n" + "=" * 80)
    print("SANIDADE DO BACKEND - ROOT")
    print("=" * 80)

    response = http_client.get("/")

    assert response.status_code == 200, (
        f"Root retornou status inesperado: {response.status_code}"
    )

    data = response.json()

    assert "service" in data, "Campo 'service' ausente no root"
    assert "version" in data, "Campo 'version' ausente no root"
    assert "status" in data, "Campo 'status' ausente no root"
    assert data["status"] == "running", (
        f"Status inesperado no root: {data['status']}"
    )

    print("Root respondeu corretamente com estrutura válida.")


# ============================================================
# HEALTHCHECK
# ============================================================

def test_health_endpoint(http_client):
    print("\n" + "=" * 80)
    print("HEALTHCHECK DO BACKEND")
    print("=" * 80)

    response = http_client.get("/health")

    assert response.status_code == 200, (
        f"Health retornou status inesperado: {response.status_code}"
    )

    data = response.json()

    assert isinstance(data, dict), "Health não retornou JSON válido"
    assert "status" in data, "Campo 'status' ausente no health"
    assert data["status"] in ("ok", "running", "healthy"), (
        f"Status inesperado no health: {data['status']}"
    )

    if "database" in data:
        assert data["database"] in ("connected", "ok", True), (
            f"Banco não está saudável: {data['database']}"
        )

    print("Health respondeu corretamente com estrutura válida.")


# ============================================================
# PERFORMANCE DO HEALTH
# ============================================================

def test_health_performance(http_client):
    print("\n" + "=" * 80)
    print("PERFORMANCE DO HEALTHCHECK")
    print("=" * 80)

    start = time.perf_counter()
    response = http_client.get("/health")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200, "Health falhou durante teste de performance"

    assert elapsed_ms < 5000, (
        f"Health demorou demais: {elapsed_ms:.2f} ms"
    )

    print(f"Health respondeu em tempo aceitável: {elapsed_ms:.2f} ms")
