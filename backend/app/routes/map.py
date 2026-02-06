"""
routes/map.py

Rotas relacionadas à visualização geográfica dos pontos críticos.
Responsável por fornecer dados prontos para renderização em mapas.
"""

from datetime import date, datetime
from typing import List

from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.point import PointResponse
from backend.app.services.risk_orchestrator import RiskOrchestrator
from backend.app.schemas.map import MapPointsResponse, MapPointSchema
from backend.app.utils.time_utils import today_utc
from backend.app.settings import settings

router = APIRouter(
    prefix="/map",
    tags=["Map"],
)

# Instância única do orquestrador
risk_orchestrator = RiskOrchestrator()


@router.get(
    "/points",
    response_model=MapPointsResponse,
    status_code=status.HTTP_200_OK,
    summary="Pontos críticos com risco para visualização em mapa",
    description=(
        "Retorna os pontos críticos monitorados, para exibição no mapa."
        "Por padrão, inclui o risco climático estimado pelo modelo ICRA."
        "pode operar em modo sem risco para carregamento rápido de localização."
    ),
)
def get_map_points(
    with_risk: bool = True,
):
    """
    Endpoint principal de integração com o frontend de mapa.

    - Carrega os pontos críticos
    - Avalia o risco de cada ponto
    - Retorna os dados consolidados
    """
    try:
        target_date = today_utc()

        points = risk_orchestrator.get_all_points()[: settings.MAP.MAX_POINTS]

        map_points: List[MapPointSchema] = []
        
        for point in points:
            if with_risk:
                try:
                    point_with_risk = risk_orchestrator.evaluate_point_risk(
                        point=point,
                        target_date=target_date,
                    )
                    
                except Exception as err:
                    print(f"[Map][RISK ERROR] Ponto {point.nome} ({point.id}): {err}")
                    point_with_risk = MapPointSchema(
                        ponto=PointResponse(
                            id=point.id,
                            nome=point.nome,
                            localizacao={
                                "latitude": point.localizacao.latitude,
                                "longitude": point.localizacao.longitude,
                            },
                            ativo=point.ativo,
                            raio_influencia_m=point.raio_influencia_m,
                            bairro=point.bairro or None,
                            descricao=point.descricao or None,
                        ),
                        risco_atual=None,
                    )
            else:
                point_with_risk = MapPointSchema(
                    ponto=PointResponse(
                        id=point.id,
                        nome=point.nome,
                        localizacao={
                            "latitude": point.localizacao.latitude,
                            "longitude": point.localizacao.longitude,
                        },
                        ativo=point.ativo,
                        raio_influencia_m=point.raio_influencia_m,
                        bairro=point.bairro or None,
                        descricao=point.descricao or None,
                    ),
                    risco_atual=None,
                )
            
            map_points.append(point_with_risk)

        return MapPointsResponse(
            pontos=map_points,
            atualizado_em=datetime.utcnow().replace(tzinfo=None),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar pontos do mapa: {e}",
        )
