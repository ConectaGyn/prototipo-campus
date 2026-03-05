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
from datetime import datetime
from typing import Optional

from backend.app.database import SessionLocal
from backend.app.settings import settings
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.services.risk_orchestrator import RiskOrchestrator
from backend.app.repositories.municipality_repository import MunicipalityRepository
from backend.app.repositories.risk_surface_repository import RiskSurfaceRepository
from backend.app.services.risk_surface_service import RiskSurfaceService
from backend.app.models.point import Point

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
        self.cycle_seconds = int(settings.RISK.SCHEDULE_INTERVAL_SECONDS)
        # Poll curto para alinhar execução aos buckets mesmo se a app iniciar fora da borda de 3h.
        self.poll_seconds = min(self.cycle_seconds, 60)
        self.enabled = bool(settings.RISK.SCHEDULER_ENABLED)
        self._last_surface_reference_ts: Optional[datetime] = None

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
                # Executa o ciclo em thread para não bloquear o event loop do FastAPI.
                await asyncio.to_thread(self._maybe_generate_snapshot)
            except Exception as e:
                print(f"[SCHEDULER][ERROR] {repr(e)}")

            await asyncio.sleep(self.poll_seconds)

    # --------------------------------------------------------
    # Núcleo
    # --------------------------------------------------------

    def _maybe_generate_snapshot(self) -> bool:
        with SessionLocal() as session:

            repo = RiskRepository(session)
            orchestrator = RiskOrchestrator(repository=repo)
            reference_ts = orchestrator.get_reference_ts_now()
            points = orchestrator.list_points(db=session, only_active=True)
            total_points = len(points)

            if total_points == 0:
                return False

            bucket_snapshots = repo.get_snapshots_by_bucket(reference_ts)
            snapshot_ids = {s.point_id for s in bucket_snapshots}
            active_ids = {p.id for p in points}
            missing_count = len(active_ids - snapshot_ids)

            # Bucket atual já completo: nada a fazer.
            if missing_count == 0:
                self._ensure_surfaces_for_bucket(
                    session=session,
                    repo=repo,
                    reference_ts=reference_ts,
                )
                return False

            print(
                "[SCHEDULER] Gerando/completando snapshot "
                f"{reference_ts.isoformat()} | total={total_points} missing={missing_count}"
            )

            result = orchestrator.compute_all_points_for_cycle(
                db=session,
                reference_ts=reference_ts,
                only_active=True,
                skip_if_exists=True,
            )

            print(f"[SCHEDULER] Resultado: {result}")
            self._ensure_surfaces_for_bucket(
                session=session,
                repo=repo,
                reference_ts=reference_ts,
            )
            return result["created"] > 0

    def _ensure_surfaces_for_bucket(
        self,
        session,
        repo: RiskRepository,
        reference_ts: datetime,
    ) -> None:
        if self._last_surface_reference_ts == reference_ts:
            return

        mrepo = MunicipalityRepository(session)
        srepo = RiskSurfaceRepository(session)
        surface_service = RiskSurfaceService(
            municipality_repo=mrepo,
            surface_repo=srepo,
            risk_repo=repo,
        )

        municipalities = mrepo.list_active_for_surface_generation()
        ok = 0
        skip_no_points = 0
        failed = 0

        for municipality in municipalities:
            has_points = (
                session.query(Point.id)
                .filter(
                    Point.active.is_(True),
                    Point.municipality_id == municipality.id,
                )
                .first()
                is not None
            )
            if not has_points:
                skip_no_points += 1
                continue

            try:
                print(
                    f"[SCHEDULER] Gerando superfície para município "
                    f"{municipality.id} - {municipality.name}"
                )
                surface_service.get_or_generate_surface(
                    db=session,
                    municipality_id=municipality.id,
                    snapshot_timestamp=reference_ts,
                    force_recompute=True,
                    source="scheduled",
                )
                ok += 1
            except Exception as e:
                failed += 1
                print(
                    "[SCHEDULER][SURFACE ERROR] "
                    f"municipality_id={municipality.id} error={repr(e)}"
                )

        print(
            "[SCHEDULER] Superfícies do bucket concluídas "
            f"{reference_ts.isoformat()} | ok={ok} skip_no_points={skip_no_points} failed={failed}"
        )
        self._last_surface_reference_ts = reference_ts
        
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
