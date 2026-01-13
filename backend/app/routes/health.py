"""
health.py

Endpoints de verificação de saúde da API Backend.

Utilizado para:
- Monitoramento
- Deploys (Railway, CI/CD)
- Verificação rápida pelo frontend
"""

from fastapi import APIRouter

from backend.app.settings import settings


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    summary="Healthcheck da API Backend",
)
def healthcheck():
    """
    Verifica se a API está operacional.

    Este endpoint NÃO executa lógica pesada.
    Deve responder rapidamente.
    """

    return {
        "status": "ok",
        "service": "backend-core",
        "version": settings.APP_VERSION,
        "environment": "debug" if settings.DEBUG else "production",
    }
