"""
points.py

Rotas relacionadas aos pontos críticos monitorados.
Responsável por fornecer dados consolidados para o frontend.
"""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException, status

from backend.app.services.risk_orchestrator import RiskOrchestrator, RiskOrchestrationError
from backend.app.schemas.point import PointResponse
from backend.app.schemas.map import RiskStatusSchema


router = APIRouter(
    prefix="/points",
    tags=["Points"],
)

_points_loader = RiskOrchestrator()

# =====================================================
# LISTAGEM DE PONTOS ESTATICOS
# =====================================================

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
    
# =====================================================
# RISCO SOB DEMANDA POR PONTO
# =====================================================

@router.get(
    "/{point_id}/risk",
    response_model=RiskStatusSchema,
    status_code=status.HTTP_200_OK,
    summary="Calcula o risco climático de um ponto especifico",
    description=(
        "Executa o cálculo de risco climático via IA apenas para o ponto solicitado"
    ),
)
def calculate_point_risk(point_id: str):
    """
    Calcula o risco climático para um ponto específico.
    Executado sob demanda (ex: clique no mapa)
    """

    try:
        points = _points_loader.get_all_points()
        point = next((p for p in points if p.id == point_id), None)

        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ponto com ID '{point_id}' não encontrado.",
            )
        
        result = _points_loader.evaluate_point_risk(
            point=point,
            target_date=date.today(),
            with_history=True,
        )

        if not result.risco_atual:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível calcular o risco no momento",
            )
        
        return result.risco_atual
    
    except HTTPException:
        raise

    except RiskOrchestrationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço de cálculo de risco indisponível no momento:",
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado ao calcular risco do ponto '{point_id}': {e}",
        )