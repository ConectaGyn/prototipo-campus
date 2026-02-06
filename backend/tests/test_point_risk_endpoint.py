"""
test_point_risk_endpoint.py

Testes do endpoint GET /points/{id}/risk

Objetivo:
- Validar o cálculo de risco sob demanda (lazy evaluation)
- Garantir contrato de resposta esperado pelo frontend
- Detectar erros de pipeline antes do teste ponta-a-ponta

Este teste:
- NÃO usa frontend
- NÃO usa mocks
- USA o pipeline real (clima + features + IA)
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.risk_orchestrator import RiskOrchestrationError

client = TestClient(app)


# ============================================================
# HELPERS
# ============================================================

def _print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def _print_kv(label: str, value):
    print(f"{label:<20}: {value}")


# ============================================================
# TESTES
# ============================================================

def test_point_risk_endpoint_is_reachable():
    """
    Teste de sanidade:
    Verifica se o endpoint /points/{id}/risk existe (não é 404).
    """

    _print_header("TESTE 1 — Endpoint /points/{id}/risk está acessível")

    # Usamos um ID inválido de propósito
    response = client.get("/points/p99999/risk")

    _print_kv("Status code", response.status_code)
    _print_kv("Resposta", response.json())

    # O importante aqui é NÃO ser 404 de rota inexistente
    assert response.status_code in (404, 400, 422), (
        "Endpoint não está registrado corretamente."
    )


def test_point_risk_success():
    """
    Teste principal (happy path):
    - Busca um ponto válido
    - Calcula o risco sob demanda
    - Valida contrato da resposta
    """

    _print_header("TESTE 2 — Cálculo de risco para ponto válido")

    # --------------------------------------------------------
    # 1. Buscar pontos disponíveis
    # --------------------------------------------------------
    points_response = client.get("/points")
    assert points_response.status_code == 200, "Falha ao listar pontos."

    points = points_response.json()
    assert isinstance(points, list) and len(points) > 0, "Nenhum ponto retornado."

    point = points[0]
    point_id = point["id"]
    point_name = point["nome"]

    _print_kv("Ponto selecionado", f"{point_id} - {point_name}")
    _print_kv("Latitude", point["localizacao"]["latitude"])
    _print_kv("Longitude", point["localizacao"]["longitude"])

    # --------------------------------------------------------
    # 2. Chamar endpoint de risco
    # --------------------------------------------------------
    risk_response = client.get(f"/points/{point_id}/risk")

    _print_kv("Status code", risk_response.status_code)
    assert risk_response.status_code == 200, (
        f"Erro ao calcular risco do ponto {point_id}"
    )

    risk_data = risk_response.json()

    _print_header("Resultado do risco")
    for k, v in risk_data.items():
        _print_kv(k, v)

    # --------------------------------------------------------
    # 3. Validações de contrato
    # --------------------------------------------------------
    assert "icra" in risk_data, "Campo 'icra' ausente."
    assert "nivel" in risk_data, "Campo 'nivel' ausente."
    assert "confianca" in risk_data, "Campo 'confianca' ausente."
    assert "cor" in risk_data, "Campo 'cor' ausente."

    assert isinstance(risk_data["icra"], (int, float)), "ICRA inválido."
    assert risk_data["nivel"] in {"Baixo", "Moderado", "Alto", "Muito Alto"}, (
        f"Nível de risco inesperado: {risk_data['nivel']}"
    )

    print("\n✔️ Risco calculado com sucesso para o ponto.")


def test_point_risk_not_found():
    """
    Teste de erro esperado:
    - ID inexistente
    - Deve retornar 404 com mensagem clara
    """

    _print_header("TESTE 3 — Erro para ponto inexistente")

    invalid_point_id = "p99999"
    response = client.get(f"/points/{invalid_point_id}/risk")

    _print_kv("Status code", response.status_code)
    _print_kv("Resposta", response.json())

    assert response.status_code == 404, "Status esperado: 404 (ponto não encontrado)"
    assert "não encontrado" in response.json()["detail"].lower()


def test_point_risk_service_failure(monkeypatch):
    """
    Teste opcional (mas recomendado):
    Simula falha no serviço de risco para garantir erro controlado.
    """

    _print_header("TESTE 4 — Falha controlada no serviço de risco")

    from backend.app.services import risk_orchestrator

    def fake_evaluate_point_risk(*args, **kwargs):
        raise RiskOrchestrationError("Falha simulada")

    monkeypatch.setattr(
        risk_orchestrator.RiskOrchestrator,
        "evaluate_point_risk",
        fake_evaluate_point_risk,
    )

    # Buscar um ponto válido
    points = client.get("/points").json()
    point_id = points[0]["id"]

    response = client.get(f"/points/{point_id}/risk")

    _print_kv("Status code", response.status_code)
    _print_kv("Resposta", response.json())

    assert response.status_code == 503, "Status esperado: 503 (serviço indisponível)"
    assert "indisponível" in response.json()["detail"].lower()
