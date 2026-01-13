"""
main.py

Ponto de entrada do Backend Core do projeto ClimaGyn.

Responsável por:
- Inicializar a aplicação FastAPI
- Registrar rotas
- Configurar metadados da API
- Definir ciclo de vida da aplicação

Este arquivo NÃO contém lógica de negócio.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from backend.app.settings import settings
from backend.app.routes.health import router as health_router
from backend.app.routes.points import router as points_router
from backend.app.routes.map import router as map_router


# =====================================================
# STARTUP
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Backend Core iniciado")
    print(f"Serviço: {settings.APP_NAME} v{settings.APP_VERSION}")

    if settings.DEBUG:
        print("Modo DEBUG ativo")

    csv_path = settings.DATA.CRITICAL_POINTS_CSV
    if not csv_path.exists():
        print(f"ATENÇÃO: CSV de pontos críticos não encontrado em {csv_path}")
    else:
        print(f"CSV de pontos críticos localizado em {csv_path}")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# REGISTRO DE ROTAS
# =====================================================

app.include_router(health_router)
app.include_router(points_router)
app.include_router(map_router)  


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
