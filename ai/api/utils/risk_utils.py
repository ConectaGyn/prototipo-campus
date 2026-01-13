"""
risk_utils.py

Funções utilitárias relacionadas à classificação de risco ICRA.

Este módulo contém apenas regras de negócio puras, sem dependência
de FastAPI, modelos de ML ou carregamento de arquivos.
"""

from typing import Dict, Optional


# =====================================================
# CLASSIFICAÇÃO DE RISCO
# =====================================================

def classificar_nivel_risco(icra_value: float, thresholds: Dict[str, float]) -> str:
    """
    Classifica o nível de risco com base no valor do ICRA e nos thresholds definidos.
    """

    required_keys = {"baixo_max", "moderado_max", "alto_max"}
    if not required_keys.issubset(thresholds):
        raise ValueError(
            f"Thresholds inválidos. Esperado: {required_keys}. "
            f"Recebido: {set(thresholds.keys())}"
        )

    if icra_value < thresholds["baixo_max"]:
        return "Baixo"
    elif icra_value < thresholds["moderado_max"]:
        return "Moderado"
    elif icra_value < thresholds["alto_max"]:
        return "Alto"
    else:
        return "Muito Alto"


# =====================================================
# CLASSIFICAÇÃO DE CONFIANÇA
# =====================================================

def classificar_confianca(icra_std: Optional[float]) -> str:
    """
    Classifica a confiança da previsão com base na incerteza (desvio padrão).

    Se a incerteza não estiver disponível, assume confiança alta.
    """

    if icra_std is None:
        return "Alta"

    if icra_std < 0.15:
        return "Alta"
    elif icra_std < 0.30:
        return "Média"
    else:
        return "Baixa"
