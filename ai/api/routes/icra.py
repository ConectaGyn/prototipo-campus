"""
icra.py

Rotas relacionadas à predição do índice ICRA.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from ai.api.schemas import (
    ICRAPredictRequest,
    ICRAPredictResponse,
)
from ai.api.services.icra_service import predict_icra


# =====================================================
# CONFIGURAÇÃO DE LOG
# =====================================================

logger = logging.getLogger(__name__)


# =====================================================
# ROUTER
# =====================================================

router = APIRouter(
    prefix="/icra",
    tags=["ICRA"],
)


# =====================================================
# ENDPOINTS
# =====================================================

@router.post(
    "/predict",
    response_model=ICRAPredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Predição de risco de alagamento (ICRA)",
    description=(
        "Executa a inferência do modelo ICRA a partir de variáveis "
        "climáticas agregadas e retorna o nível de risco estimado."
    ),
)
def predict_icra_endpoint(
    payload: ICRAPredictRequest,
) -> ICRAPredictResponse:
    """
    Endpoint de predição do índice ICRA.

    - Erros de validação de features retornam 422
    - Erros internos retornam 500
    """

    try:
        return predict_icra(payload)

    except ValueError as e:
        # Erro de contrato (features ausentes, formato inválido, etc.)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Erro de validação do payload de inferência.",
                "error": str(e),
            },
        )

    except Exception as e:
        # Erro interno inesperado
        logger.exception("Erro interno na predição ICRA")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a predição ICRA.",
        )
