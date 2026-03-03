"""
risk_orchestrator.py

Camada central de orquestração de risco do backend.

Este arquivo:
- NÃO deve depender de schemas de API (isso fica em routes/schemas)
- Usa Repository para persistência
- Usa session por requisição (session injetada pelas rotas/serviços)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from sqlalchemy.orm import Session

from backend.app.settings import settings
from backend.app.models.point import Point
from backend.app.models.risk_snapshot import RiskSnapshot
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.services.climate_service import ClimateService
from backend.app.services.feature_builder import FeatureBuilder, FEATURE_ORDER


# ============================================================
# EXCEÇÕES
# ============================================================


class RiskOrchestrationError(RuntimeError):
    """Erro na orquestração de risco."""


# ============================================================
# DTOs internos (não são schemas de API)
# ============================================================


@dataclass(frozen=True)
class RiskResult:
    point_id: str
    reference_ts: datetime
    icra: float
    icra_std: float
    nivel_risco: str
    confianca: str
    chuva_dia: float
    chuva_30d: float
    chuva_90d: float


# ============================================================
# ORQUESTRATOR
# ============================================================


class RiskOrchestrator:
    """
    Orquestrador principal.
    """

    def __init__(
        self,
        repository: RiskRepository,
        climate_service: Optional[ClimateService] = None,
        feature_builder: Optional[FeatureBuilder] = None,
        http_session: Optional[requests.Session] = None,
    ) -> None:
        self.repo = repository
        self.climate_service = climate_service or ClimateService()
        self.feature_builder = feature_builder or FeatureBuilder()
        self.http = http_session or requests.Session()
        self.history_days: int = int(getattr(getattr(settings, "RISK", object()), "HISTORY_DAYS", 90))
        self.snapshot_ttl_seconds: int = int(settings.RISK.SNAPSHOT_TTL_SECONDS)
        interval_seconds = int(settings.RISK.SCHEDULE_INTERVAL_SECONDS)
        self.rounding_minutes: int = max(1, interval_seconds // 60)

    # --------------------------------------------------------
    # PÚBLICOS (chamados por rotas / scheduler)
    # --------------------------------------------------------

    def list_points(self, db: Session, only_active: bool = True) -> List[Point]:
        q = db.query(Point)
        if only_active:
            q = q.filter(Point.active.is_(True))
        return q.order_by(Point.id.asc()).all()

    def get_point(self, db: Session, point_id: str) -> Point:
        p = db.query(Point).filter(Point.id == point_id).one_or_none()
        if not p:
            raise RiskOrchestrationError(f"Ponto não encontrado: {point_id}")
        return p

    def get_reference_ts_now(self) -> datetime:
        """
        Gera um timestamp “exato” arredondado para janelas (ex: 3 em 3 horas).
        Isso vira a chave do snapshot e garante que todos os usuários vejam o mesmo “ciclo”.
        """
        now = datetime.now(timezone.utc)
        return self._round_ts(now, minutes=self.rounding_minutes)

    def get_latest_map_state(
        self,
        db: Session,
        reference_ts: Optional[datetime] = None,
        only_active: bool = True,
    ) -> Tuple[datetime, List[Tuple[Point, Optional[RiskSnapshot]]]]:
        """
        Retorna:
        - reference_ts (ciclo)
        - lista de (Point, snapshot_do_ciclo_ou_None)

        Estratégia:
        - Para o mapa “rápido”, busca snapshots exatamente do ciclo reference_ts.
        - Se não existir snapshot naquele ciclo para um ponto, retorna None.
          (O frontend pode mostrar cinza/indisponível e permitir fallback sob demanda)
        """
        ref = reference_ts or self.get_reference_ts_now()
        points = self.list_points(db, only_active=only_active)

        snapshots = self.repo.get_all_by_timestamp(ref)
        snapshots_by_point = {s.point_id: s for s in snapshots}

        out: List[Tuple[Point, Optional[RiskSnapshot]]] = []
        for p in points:
            out.append((p, snapshots_by_point.get(p.id)))
        return ref, out

    def get_or_compute_point_snapshot(
        self,
        db: Session,
        point_id: str,
        reference_ts: Optional[datetime] = None,
        force_recompute: bool = False,
    ) -> RiskSnapshot:
        """
        Fallback sob demanda:
        - Se já existe snapshot “fresco” do ciclo, devolve.
        - Se não existe / expirou / force=True, recalcula e salva.
        """
        ref = reference_ts or self.get_reference_ts_now()
        point = self.get_point(db, point_id)

        if not force_recompute:
            latest = self.repo.get_latest_by_point(point_id)
            if latest and latest.snapshot_timestamp == ref:
                if not self._is_expired(latest):
                    return latest

        computed = self._compute_point_risk(point=point, reference_ts=ref, source="on_demand") 
        saved = self.repo.save_snapshot(computed)
        return saved

    def compute_all_points_for_cycle(
        self,
        db: Session,
        reference_ts: Optional[datetime] = None,
        only_active: bool = True,
        skip_if_exists: bool = True,
    ) -> Dict[str, Any]:
        """
        Scheduler:
        - Calcula snapshot para todos os pontos do ciclo `reference_ts`
        - Persiste no banco
        - Retorna um pequeno resumo para logs/observabilidade
        """
        ref = reference_ts or self.get_reference_ts_now()
        points = self.list_points(db, only_active=only_active)

        created = 0
        reused = 0
        failed: List[Dict[str, str]] = []

        for p in points:
            try:
                if skip_if_exists:
                    latest = self.repo.get_latest_by_point(p.id)
                    if latest and latest.snapshot_timestamp == ref:
                        reused += 1
                        continue

                snap = self._compute_point_risk(point=p, reference_ts=ref, source="scheduler")
                self.repo.save_snapshot(snap)
                created += 1

            except Exception as e:
                failed.append({"point_id": p.id, "error": repr(e)})

        return {
            "reference_ts": ref.isoformat(),
            "total_points": len(points),
            "created": created,
            "reused": reused,
            "failed_count": len(failed),
            "failed": failed[:10],
        }

    # --------------------------------------------------------
    # CÁLCULO REAL (clima -> features -> IA -> snapshot)
    # --------------------------------------------------------

    def _compute_point_risk(self, point: Point, reference_ts: datetime, source: str = "on_demand") -> RiskSnapshot:
        """
        Computa risco de um ponto para um reference_ts.
        """
        target_date = reference_ts.date()
        start_date = target_date - timedelta(days=self.history_days)
        end_date = target_date

        # 1) Clima 
        climate_today, climate_history = self._get_climate_inputs(
            latitude=float(point.latitude),
            longitude=float(point.longitude),
            start_date=start_date,
            end_date=end_date,
            target_date=target_date,
        )

        # 2) Features 
        features = self.feature_builder.build_features(
            climate_today=climate_today,
            climate_history=climate_history,
            target_date=target_date,
        )

        # Garante ordem/keys esperadas pela IA
        features_ordered = {k: float(features.get(k, 0.0)) for k in FEATURE_ORDER}

        # 3) IA
        icra_result = self._call_icra_api(
            point_id=point.id,
            target_date=target_date,
            features=features_ordered,
        )

        # 4) Persistência 
        nivel = self._normalize_risk_level(str(icra_result.get("nivel_risco", "")))
        confianca = str(icra_result.get("confianca", "Indefinida"))

        detalhes = icra_result.get("detalhes") or {}
        chuva_dia = float(detalhes.get("chuva_dia", features_ordered.get("precipitacao_total_mm", 0.0)))
        chuva_30d = float(detalhes.get("chuva_30d", features_ordered.get("precipitacao_ma_30d", 0.0)))
        chuva_90d = float(detalhes.get("chuva_90d", features_ordered.get("precipitacao_ma_90d", 0.0)))

        now = datetime.now(timezone.utc)

        return RiskSnapshot(
            point_id=point.id,
            snapshot_timestamp=reference_ts,
            icra=float(icra_result.get("icra", 0.0)),
            icra_std=float(icra_result.get("icra_std", 0.0)),
            nivel_risco=nivel,
            confianca=confianca,
            chuva_dia=chuva_dia,
            chuva_30d=chuva_30d,
            chuva_90d=chuva_90d,
            source=source,
            
        )

    def _get_climate_inputs(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        target_date: date,
    ) -> Tuple[Dict[str, Any], Dict[str, List[float]]]:
        """
        Retorna:
        - climate_today: dict (precipitacao_total_mm, temperatura_media_2m_C, ...)
        - climate_history: dict com séries list[float] p/ precip e temp
        """
        if hasattr(self.climate_service, "get_daily_series"):
            series = self.climate_service.get_daily_series(
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
            )

            climate_today, history = self._series_to_today_and_history(series, target_date=target_date)
            return climate_today, history

        if not hasattr(self.climate_service, "get_daily_climate"):
            raise RiskOrchestrationError(
                "ClimateService não possui get_daily_series nem get_daily_climate."
            )

        climate_today = self.climate_service.get_daily_climate(
            latitude=latitude,
            longitude=longitude,
            target_date=target_date,
        )

        precip_series: List[float] = []
        temp_series: List[float] = []
        total_days = (end_date - start_date).days
        for i in range(1, total_days + 1):
            d = target_date - timedelta(days=i)
            past = self.climate_service.get_daily_climate(latitude=latitude, longitude=longitude, target_date=d)
            precip_series.append(float(past.get("precipitacao_total_mm", 0.0)))
            temp_series.append(float(past.get("temperatura_media_2m_C", 0.0)))

        history = {
            "precipitacao_total_mm": precip_series,
            "temperatura_media_2m_C": temp_series,
        }
        return climate_today, history

    def _series_to_today_and_history(
        self,
        series: Any,
        target_date: date,
    ) -> Tuple[Dict[str, Any], Dict[str, List[float]]]:
        """
        Converte série diária (de qualquer formato comum) para:
        - climate_today: dict
        - climate_history: dict com listas (passado), onde index 0 é "ontem" etc.
        """
        if isinstance(series, list) and (len(series) == 0 or isinstance(series[0], dict)):
            by_date: Dict[str, Dict[str, Any]] = {}
            for item in series:
                d = str(item.get("date") or item.get("data") or "").strip()
                if not d:
                    continue
                by_date[d] = item

            td = target_date.isoformat()
            today_item = by_date.get(td)
            if not today_item:
                today_item = by_date[sorted(by_date.keys())[-1]] if by_date else {}

            climate_today = {
                "precipitacao_total_mm": float(today_item.get("precipitacao_total_mm", 0.0) or 0.0),
                "temperatura_media_2m_C": float(today_item.get("temperatura_media_2m_C", 0.0) or 0.0),
                "temperatura_aparente_media_2m_C": float(today_item.get("temperatura_aparente_media_2m_C", 0.0) or 0.0),
            }

            precip_series: List[float] = []
            temp_series: List[float] = []
            for i in range(1, self.history_days + 1):
                d = (target_date - timedelta(days=i)).isoformat()
                it = by_date.get(d, {})
                precip_series.append(float(it.get("precipitacao_total_mm", 0.0) or 0.0))
                temp_series.append(float(it.get("temperatura_media_2m_C", 0.0) or 0.0))

            climate_history = {
                "precipitacao_total_mm": precip_series,
                "temperatura_media_2m_C": temp_series,
            }
            return climate_today, climate_history

        if isinstance(series, dict):
            dates = series.get("dates") or series.get("date") or series.get("time") or []
            precip = series.get("precip") or series.get("precipitacao_total_mm") or series.get("precipitation") or []
            temp = series.get("temp") or series.get("temperatura_media_2m_C") or series.get("temperature") or []
            apparent = series.get("apparent_temp") or series.get("temperatura_aparente_media_2m_C") or series.get("apparent_temperature") or []

            dates = [str(d)[:10] for d in dates] if isinstance(dates, list) else []
            precip = list(precip) if isinstance(precip, list) else []
            temp = list(temp) if isinstance(temp, list) else []
            apparent = list(apparent) if isinstance(apparent, list) else []

            by_date_idx = {d: i for i, d in enumerate(dates)}
            td = target_date.isoformat()
            idx_today = by_date_idx.get(td)
            if idx_today is None and dates:
                idx_today = len(dates) - 1

            def _safe(arr: List[Any], idx: Optional[int]) -> float:
                if idx is None:
                    return 0.0
                try:
                    return float(arr[idx])
                except Exception:
                    return 0.0

            climate_today = {
                "precipitacao_total_mm": _safe(precip, idx_today),
                "temperatura_media_2m_C": _safe(temp, idx_today),
                "temperatura_aparente_media_2m_C": _safe(apparent, idx_today),
            }

            precip_series: List[float] = []
            temp_series: List[float] = []
            for i in range(1, self.history_days + 1):
                d = (target_date - timedelta(days=i)).isoformat()
                idx = by_date_idx.get(d)
                precip_series.append(_safe(precip, idx))
                temp_series.append(_safe(temp, idx))

            climate_history = {
                "precipitacao_total_mm": precip_series,
                "temperatura_media_2m_C": temp_series,
            }
            return climate_today, climate_history

        raise RiskOrchestrationError("Formato de série climática não reconhecido.")

    # --------------------------------------------------------
    # CHAMADA IA + NORMALIZAÇÕES
    # --------------------------------------------------------

    def _call_icra_api(self, point_id: str, target_date: date, features: Dict[str, float]) -> Dict[str, Any]:
        payload = {
            "data": target_date.isoformat(),
            "features": features,
            "ponto": point_id,
        }

        url = f"{settings.IA.BASE_URL}{settings.IA.PREDICT_ENDPOINT}"
        timeout = int(getattr(settings.IA, "TIMEOUT_SECONDS", 30))

        try:
            resp = self.http.post(url, json=payload, timeout=timeout)
        except Exception as e:
            raise RiskOrchestrationError(f"Falha ao chamar ICRA: {repr(e)}") from e

        if resp.status_code != 200:
            raise RiskOrchestrationError(f"ICRA retornou {resp.status_code}: {resp.text[:500]}")

        try:
            return resp.json()
        except Exception as e:
            raise RiskOrchestrationError(
                f"ICRA retornou JSON inválido: {repr(e)} | body={resp.text[:500]}"
            ) from e

    def _normalize_risk_level(self, raw: str) -> str:
        if not raw:
            return "Moderado"
        v = raw.strip().lower().replace("-", "_").replace(" ", "_")
        mapping = {
            "baixo": "Baixo",
            "moderado": "Moderado",
            "alto": "Alto",
            "muito_alto": "Muito Alto",
            "muitoalto": "Muito Alto",
        }
        normalized = mapping.get(v)
        if normalized:
            return normalized
        
        return "Moderado"

    # --------------------------------------------------------
    # UTILITÁRIOS
    # --------------------------------------------------------

    def _is_expired(self, snapshot: RiskSnapshot) -> bool:
        if not snapshot.snapshot_timestamp:
            return False
        expires_at = snapshot.snapshot_timestamp + timedelta(
            seconds=self.snapshot_ttl_seconds
        )
        return datetime.now(timezone.utc) > expires_at

    def _round_ts(self, ts: datetime, minutes: int) -> datetime:
        """
        Arredonda para baixo no múltiplo de `minutes` (UTC).
        Ex: minutes=180 => 00:00, 03:00, 06:00, ...
        """
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        total_minutes = ts.hour * 60 + ts.minute
        rounded = (total_minutes // minutes) * minutes

        hour = rounded // 60
        minute = rounded % 60

        return ts.replace(hour=hour, minute=minute, second=0, microsecond=0)
