"""
conftest.py

Infraestrutura central da suíte de testes E2E do ClimaGyn.

Responsável por:
- Validar backend antes de qualquer teste
- Validar IA 
- Validar banco populado
- Criar HTTP client reutilizável
- Fornecer logs estruturados
- Abortar execução se ambiente estiver inconsistente

NÃO contém lógica de teste.
"""

import os
import sys
import time
import pytest
import requests
from backend.app.tests.utils.http_client import APIClient
from backend.app.scripts.seed_municipality import seed_municipalities
from backend.app.scripts.seed_points import seed_points


# ============================================================
# CONFIGURAÇÃO GLOBAL
# ============================================================

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
IA_URL = os.getenv("E2E_IA_URL", "http://localhost:8501")
TIMEOUT = int(os.getenv("E2E_TIMEOUT_SECONDS", "30"))


# ============================================================
# LOG ESTRUTURADO
# ============================================================

def _print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def _print_ok(msg: str):
    print(f"{msg}")

def _print_error(msg: str):
    print(f"{msg}")

# ============================================================
# VALIDAÇÃO DO BACKEND
# ============================================================

def _validate_backend():
    _print_header("VALIDAÇÃO DO BACKEND")

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    except Exception as e:
        _print_error(f"Não foi possível conectar ao backend: {e}")
        pytest.exit("Backend não está acessível.")

    if response.status_code != 200:
        _print_error(f"Backend respondeu status {response.status_code}")
        pytest.exit("Backend não saudável.")

    data = response.json()

    if data.get("status") != "ok":
        _print_error("Backend health retornou status != ok")
        pytest.exit("Backend não saudável.")

    _print_ok("Backend saudável")


# ============================================================
# VALIDAÇÃO DA IA
# ============================================================

def _validate_ia():
    _print_header("VALIDAÇÃO DA IA")

    try:
        response = requests.get(f"{IA_URL}/health", timeout=TIMEOUT)
    except Exception:
        _print_error("IA não está acessível.")
        pytest.exit("Módulo de IA não está rodando.")

    if response.status_code != 200:
        _print_error(f"IA respondeu status {response.status_code}")
        pytest.exit("IA não saudável.")

    _print_ok("IA saudável")

# ============================================================
# SEED AUTOMÁTICO
# ============================================================

def _run_seeds():
    _print_header("EXECUTANDO SEEDS AUTOMÁTICOS")

    try:
        muni_result = seed_municipalities()
        _print_ok(
            f"Seed Municípios → "
            f"Inseridos: {muni_result['inserted']} | "
            f"Ignorados: {muni_result['ignored']} | "
            f"Erros: {muni_result['errors']}"
        )

        points_result = seed_points()
        _print_ok(
            f"Seed Pontos → "
            f"Inseridos: {points_result['inserted']} | "
            f"Ignorados: {points_result['ignored']} | "
            f"Erros: {points_result['errors']}"
        )

    except Exception as e:
        _print_error(f"Erro ao executar seeds: {e}")
        pytest.exit("Falha crítica na execução dos seeds.")


# ============================================================
# VALIDAÇÃO DO BANCO POPULADO
# ============================================================

def _validate_database_population():
    _print_header("VALIDAÇÃO DO BANCO")

    try:
        response = requests.get(f"{BASE_URL}/municipalities", timeout=TIMEOUT)
        if response.status_code != 200:
            pytest.exit("Falha ao consultar municípios.")

        municipalities = response.json()
        if not municipalities:
            pytest.exit("Nenhum município encontrado no banco.")

        _print_ok(f"{len(municipalities)} município(s) encontrado(s)")

        response = requests.get(f"{BASE_URL}/points", timeout=TIMEOUT)
        if response.status_code != 200:
            pytest.exit("Falha ao consultar pontos.")

        points = response.json()
        if not points:
            pytest.exit("Nenhum ponto encontrado no banco.")

        _print_ok(f"{len(points)} ponto(s) encontrado(s)")

    except Exception as e:
        _print_error(f"Erro ao validar banco: {e}")
        pytest.exit("Banco inconsistente.")


# ============================================================
# FIXTURE DE VALIDAÇÃO GLOBAL
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def validate_environment():
    """
    Executado uma única vez antes de todos os testes.
    """
    _validate_backend()
    _validate_ia()
    _run_seeds()
    _validate_database_population()

    print("\nAmbiente validado com sucesso.\n")

    yield

# ============================================================
# FIXTURE HTTP CLIENT REUTILIZÁVEL
# ============================================================

@pytest.fixture(scope="session")
def http_client():
    """
    Cliente HTTP real reutilizável.
    """

    client = APIClient(
        base_url=BASE_URL,
        timeout=TIMEOUT,
        verbose=True,
    )

    print("\n" + "=" * 80)
    print("CLIENTE HTTP E@E INICIALIZADO")
    print(f"BASE URL: {client.base_url}")
    print("=" * 80)

    yield client

# ============================================================
# HOOK PARA LOGAR INÍCIO DE CADA TESTE
# ============================================================

def pytest_runtest_call(item):
    _print_header(f"EXECUTANDO: {item.name}")
    start = time.time()
    yield
    duration = time.time() - start
    print(f"Duração: {duration:.2f}s")
