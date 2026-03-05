"""
risk_relative.py

Classificacao relativa de risco por ciclo global (snapshot_timestamp).
"""

from __future__ import annotations

from typing import Dict, List


def compute_relative_levels_by_point(snapshots: List[object]) -> Dict[str, str]:
    """
    Distribui pontos em quartis de risco relativo com base no rank do ICRA no ciclo.

    Regras:
    - 0-25%   -> Baixo
    - 25-50%  -> Moderado
    - 50-75%  -> Alto
    - 75-100% -> Muito Alto
    """
    valid = []
    for s in snapshots:
        point_id = getattr(s, "point_id", None)
        icra = getattr(s, "icra", None)
        if not point_id:
            continue
        if icra is None:
            continue
        valid.append((str(point_id), float(icra)))

    if not valid:
        return {}

    # Ordenação determinística para evitar instabilidade em empates de ICRA.
    valid.sort(key=lambda x: (x[1], x[0]))
    n = len(valid)
    out: Dict[str, str] = {}

    for idx, (point_id, _icra) in enumerate(valid):
        pct = (idx + 1) / n
        if pct <= 0.25:
            level = "Baixo"
        elif pct <= 0.50:
            level = "Moderado"
        elif pct <= 0.75:
            level = "Alto"
        else:
            level = "Muito Alto"
        out[point_id] = level

    return out
