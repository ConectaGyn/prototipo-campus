"""
points.py

Rotas relacionadas aos pontos críticos monitorados.
Responsável por fornecer dados consolidados para o frontend.
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.services.risk_orchestrator import RiskOrchestrator
from backend.app.schemas.point import PointResponse


router = APIRouter(
    prefix="/points",
    tags=["Points"],
)

_points_loader = RiskOrchestrator()

@router.get(
    "",
    response_model=list[PointResponse],
    status_code=status.HTTP_200_OK,
    summary="Lista de pontos críticos monitorados",
    description=(
        "Retorna todos os pontos críticos monitorados, "
        "com localização e metadados básicos."
    ),
)
def list_points():
    """
    Lista todos os pontos críticos carregados do CSV oficial.
    Não executa cálculo de risco (apenas dados estáticos).
    """

    try:
        points = _points_loader.get_all_points()

        # Conversão explícita para schema de resposta
        return [
            PointResponse(
                id=p.id,
                nome=p.nome,
                localizacao={
                    "latitude": p.localizacao.latitude,
                    "longitude": p.localizacao.longitude,
                },
                ativo=bool(p.ativo),
                raio_influencia_m=p.raio_influencia_m,
                bairro=p.bairro or None,
                descricao=p.descricao or None,
            )
            for p in points
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar pontos críticos: {e}",
        )
