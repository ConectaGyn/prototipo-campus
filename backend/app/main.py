"""
main.py

Ponto de entrada do Backend Core do projeto ClimaGyn.

Responsável por:
- Inicializar aplicação FastAPI
- Configurar logging
- Inicializar banco de dados
- Inicializar scheduler (se habilitado)
- Registrar rotas
- Definir ciclo de vida da aplicação

Este arquivo NÃO contém lógica de negócio.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.settings import settings
from backend.app.database import init_database, close_database
from backend.app.routes.health import router as health_router
from backend.app.routes.points import router as points_router
from backend.app.routes.map import router as map_router
from backend.app.routes.surface import router as surface_router
from backend.app.routes.municipalities import router as municipalities_router
from backend.app.routes.analitycs import router as analytics_router

try:
    from backend.app.services.risk_scheduler import start_scheduler, stop_scheduler
    SCHEDULER_AVAILABLE = True
except Exception:
    SCHEDULER_AVAILABLE = False


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("climagyn.backend")


# =====================================================
# LIFESPAN
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Controla ciclo de vida da aplicação.
    """

    logger.info("Iniciando Backend Core")
    logger.info(f"Serviço: {settings.APP_NAME} v{settings.APP_VERSION}")

    # --------------------------------------------
    # Banco de dados
    # --------------------------------------------
    try:
        init_database()
        logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.exception("Erro ao inicializar banco de dados")
        raise e

    # --------------------------------------------
    # Scheduler
    # --------------------------------------------
    if settings.RISK.SCHEDULER_ENABLED and SCHEDULER_AVAILABLE:
        try:
            start_scheduler()
            logger.info("Scheduler de risco iniciado")
        except Exception:
            logger.exception("Erro ao iniciar scheduler")

    yield

    # --------------------------------------------
    # Shutdown
    # --------------------------------------------
    logger.info("Encerrando Backend Core")

    if settings.RISK.SCHEDULER_ENABLED and SCHEDULER_AVAILABLE:
        try:
            stop_scheduler()
            logger.info("Scheduler encerrado")
        except Exception:
            logger.exception("Erro ao encerrar scheduler")

    try:
        close_database()
        logger.info("Conexão com banco encerrada")
    except Exception:
        logger.exception("Erro ao encerrar banco de dados")


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
# CORS
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS.CORS_ALLOWED_ORIGINS,
    allow_credentials=settings.CORS.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS.CORS_ALLOW_HEADERS,
)
 
# =====================================================
# REGISTRO DE ROTAS
# =====================================================

app.include_router(health_router)
app.include_router(points_router)
app.include_router(map_router)
app.include_router(municipalities_router)
app.include_router(surface_router)
app.include_router(analytics_router)


# =====================================================
# ROOT
# =====================================================

@app.get("/", tags=["Root"])
def root():
    """
    Endpoint raiz informativo.
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }
