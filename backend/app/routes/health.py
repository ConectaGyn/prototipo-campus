"""
routes/health.py

Endpoints de verificação de saúde do Backend ClimaGyn.

Responsabilidades:
- Liveness (API está viva?)
- Readiness (Sistema pronto para atender?)
- Deep check (verificação estendida opcional)

Este módulo:
- NÃO executa cálculo de risco
- NÃO chama Open-Meteo
- NÃO executa engenharia de features
- NÃO recalcula snapshots

Ele apenas verifica estado operacional.
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.settings import settings
from backend.app.database import get_db
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.utils.time_utils import utc_now


router = APIRouter(
    tags=["Health"],
)

@router.get("/health", summary="health check da aplicação")
def health():
    """
    Endpoint simples para verificação da saúde da API.
    """
    return {
        "status": "ok",
        "database": "ok"
    }

# =====================================================
# LIVENESS
# =====================================================

@router.get("/live", summary="Liveness check")
def health_live():
    """
    Verifica se a API está viva.

    Não executa chamadas externas.
    Não verifica banco.
    """
    return {
        "status": "alive",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# =====================================================
# READINESS
# =====================================================

@router.get("/ready", summary="Readiness check")
def health_ready(db: Session = Depends(get_db)):
    """
    Verifica se o sistema está pronto para atender requisições.

    Verifica:
    - Conexão com banco
    - Existência de snapshot
    - Validade do snapshot (TTL)
    """

    # -----------------------------
    # Verificação Banco
    # -----------------------------
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database indisponível: {e}",
        )

    # -----------------------------
    # Verificação Snapshot
    # -----------------------------
    repo = RiskRepository(db)
    latest_bucket = repo.get_latest_bucket_timestamp()

    if not latest_bucket:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nenhum snapshot de risco disponível",
        )

    now = utc_now()
    ttl = timedelta(seconds=settings.SNAPSHOT_TTL_SECONDS)

    is_valid = (latest_bucket + ttl) > now

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Snapshot expirado",
        )

    return {
        "status": "ready",
        "database": database_status,
        "snapshot": {
            "timestamp": latest_bucket.isoformat(),
            "valid": True,
            "ttl_seconds": settings.SNAPSHOT_TTL_SECONDS,
        },
    }


# =====================================================
# DEEP CHECK
# =====================================================

@router.get("/deep", summary="Deep health check")
def health_deep(db: Session = Depends(get_db)):
    """
    Verificação estendida do sistema.

    Verifica:
    - Banco
    - Snapshot válido
    - Conectividade com IA (endpoint health)
    """

    # -----------------------------
    # Banco
    # -----------------------------
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database indisponível: {e}",
        )

    # -----------------------------
    # Snapshot
    # -----------------------------
    repo = RiskRepository(db)
    latest_snapshot = repo.get_latest_bucket_timestamp()

    snapshot_info = {
        "exists": False,
        "valid": False,
        "timestamp": None,
    }

    if latest_snapshot:
        snapshot_info["exists"] = True
        snapshot_info["timestamp"] = latest_snapshot.isoformat()

        ttl = timedelta(seconds=settings.SNAPSHOT_TTL_SECONDS)
        snapshot_info["valid"] = (
            latest_snapshot + ttl
        ) > utc_now()

    # -----------------------------
    # IA Health Check
    # -----------------------------
    import requests

    ia_status = "unknown"
    try:
        response = requests.get(
            settings.IA.BASE_URL + settings.IA.HEALTH_ENDPOINT,
            timeout=settings.IA.TIMEOUT_SECONDS,
        )
        ia_status = "ok" if response.status_code == 200 else "error"
    except Exception:
        ia_status = "unreachable"

    return {
        "status": "ok",
        "database": database_status,
        "snapshot": snapshot_info,
        "ia_service": ia_status,
    }
