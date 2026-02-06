"""
main.py

Ponto de entrada da API de Inteligência Artificial do projeto.
Responsável por inicializar a aplicação FastAPI, carregar os modelos
e registrar rotas.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from ai.api.settings import settings
from ai.api.routes.icra import router as icra_router
from ai.api.loaders.model_loader import (
    load_artifacts,
    get_icra_features,
    get_icra_thresholds,
)
from ai.api.schemas import ModelInfoResponse


# =====================================================
# LIFESPAN (STARTUP / SHUTDOWN)
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Carrega os artefatos do modelo no startup.
    """
    try:
        load_artifacts()
        print("✅ Artefatos do modelo ICRA carregados com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao carregar artefatos do modelo: {e}")
        raise RuntimeError("Falha crítica na inicialização da API.") from e

    yield


# =====================================================
# APLICAÇÃO FASTAPI
# =====================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# =====================================================
# REGISTRO DE ROTAS
# =====================================================

app.include_router(icra_router)


# =====================================================
# ENDPOINTS AUXILIARES
# =====================================================

@app.get(
    "/health",
    tags=["Health"],
    summary="Healthcheck da API",
)
def healthcheck():
    """
    Endpoint simples para verificação de disponibilidade da API.
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get(
    "/model/info",
    response_model=ModelInfoResponse,
    tags=["Model"],
    summary="Informações do modelo ICRA carregado",
)
def model_info():
    """
    Retorna metadados do modelo carregado em memória.
    Útil para debug, auditoria e integração frontend.
    """
    try:
        return ModelInfoResponse(
            modelo="ICRA",
            versao=settings.MODEL.VERSION,
            features=get_icra_features(),
            thresholds=get_icra_thresholds(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao recuperar informações do modelo: {e}",
        )
