"""
risk_scheduler.py

Scheduler responsável por gerar snapshots globais
de risco para todos os pontos ativos.

Compatível com a arquitetura atual:
- Usa RiskOrchestrator
- Usa RiskRepository
- Usa compute_all_points_for_cycle()
- Snapshot por bucket global
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.app.database import SessionLocal
from backend.app.settings import settings
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.services.risk_orchestrator import RiskOrchestrator
from backend.app.repositories.municipality_repository import MunicipalityRepository
from backend.app.repositories.risk_surface_repository import RiskSurfaceRepository
from backend.app.services.risk_surface_service import RiskSurfaceService

# ============================================================
# Helpers
# ============================================================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# Scheduler
# ============================================================

class RiskScheduler:
    """
    Scheduler simples e alinhado com o modelo atual.

    Responsável por:
    - Verificar se snapshot global expirou
    - Gerar novo ciclo via orchestrator
    """

    def __init__(self) -> None:
        self.ttl_seconds = int(settings.RISK.SNAPSHOT_TTL_SECONDS)
        self.poll_seconds = int(settings.RISK.SCHEDULE_INTERVAL_SECONDS)
        self.enabled = bool(settings.SCHEDULER_ENABLED)

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # --------------------------------------------------------
    # Controle
    # --------------------------------------------------------

    def start(self) -> Optional[asyncio.Task]:
        if not self.enabled:
            print("[SCHEDULER] Desabilitado.")
            return None

        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._loop())
        print("[SCHEDULER] Iniciado.")
        return self._task

    def stop(self) -> None:
        self._stop_event.set()

    # --------------------------------------------------------
    # Loop
    # --------------------------------------------------------

    async def _loop(self):
        while not self._stop_event.is_set():
            try:
                self._maybe_generate_snapshot()
            except Exception as e:
                print(f"[SCHEDULER][ERROR] {repr(e)}")

            await asyncio.sleep(self.poll_seconds)

    # --------------------------------------------------------
    # Núcleo
    # --------------------------------------------------------

    def _maybe_generate_snapshot(self) -> bool:
        with SessionLocal() as session:

            repo = RiskRepository(session)
            latest_ts = repo.get_latest_bucket_timestamp()

            now = _utcnow()

            if latest_ts:
                delta = now - latest_ts
                if delta < timedelta(seconds=self.ttl_seconds):
                    return False

            orchestrator = RiskOrchestrator(repository=repo)

            reference_ts = orchestrator.get_reference_ts_now()

            print(f"[SCHEDULER] Gerando snapshot {reference_ts.isoformat()}")

            result = orchestrator.compute_all_points_for_cycle(
                db=session,
                reference_ts=reference_ts,
                only_active=True,
                skip_if_exists=True,
            )

            print(f"[SCHEDULER] REsultado: {result}")
# ============================================================
# GERAR SUPERFÍCIE POR MUNICÍPIO
# ============================================================
            try:
                mrepo = MunicipalityRepository(session)
                srepo = RiskSurfaceRepository(session)
                surface_service = RiskSurfaceService(
                    municipality_repo=mrepo,
                    surface_repo=srepo,
                    risk_repo=repo,
                )

                municipalities = mrepo.list_active()

                for municipality in municipalities:
                    print(
                        f"[SCHEDULER] Gerando superfície para município"
                        f"{municipality.id} - {municipality.name}"
                    )

                    surface_service.get_or_generate_surface(
                        db=session,
                        municipality_id=municipality.id,
                        snapshot_timestamp=reference_ts,
                        force_recompute=False,
                        source="scheduled",
                    )
            except Exception as e:
                print(f"[SCHEDULER][SURFACE ERROR] {repr(e)}")
            return result["created"] > 0
        
# ============================================================
# Instância global
# ============================================================

risk_scheduler = RiskScheduler()


def start_scheduler():
    return risk_scheduler.start()


def stop_scheduler():
    risk_scheduler.stop()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    ok = risk_scheduler._maybe_generate_snapshot()
    print("[SCHEDULER] Snapshot gerado?", ok)
