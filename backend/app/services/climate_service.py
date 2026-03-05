"""
climate_service.py

Serviço responsável por obter dados climáticos externos
exclusivamente via Open-Meteo e normalizá-los para uso interno.

Este módulo:
- NÃO calcula risco
- NÃO monta features
- NÃO conhece IA
- NÃO persiste dados

Ele apenas fornece séries climáticas confiáveis.
"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Dict

import requests

from backend.app.settings import settings


# =====================================================
# EXCEÇÕES
# =====================================================

class ClimateServiceError(Exception):
    """Erro ao obter dados climáticos externos."""


# =====================================================
# SERVIÇO PRINCIPAL
# =====================================================

class ClimateService:
    """
    Serviço de integração com Open-Meteo.

    Fornece séries diárias agregadas para uso
    no cálculo de features e risco.
    """

    def __init__(self) -> None:
        self.base_archive_url = "https://archive-api.open-meteo.com/v1/archive"
        self.base_forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.timeout = settings.CLIMATE.CLIMATE_TIMEOUT_SECONDS

        self._session = requests.Session()

    # -------------------------------------------------
    # API PÚBLICA
    # -------------------------------------------------

    def get_daily_series(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """
        Retorna série diária agregada entre start_date e end_date.

        Parâmetros
        ----------
        latitude : float
        longitude : float
        start_date : date
        end_date : date

        Retorno
        -------
        List[Dict]
            Lista de registros normalizados por dia.
        """

        if start_date > end_date:
            raise ClimateServiceError("start_date não pode ser maior que end_date")

        url = self._select_endpoint(end_date)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "precipitation_sum,temperature_2m_mean,apparent_temperature_mean",
            "timezone": "UTC",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        max_retries = settings.CLIMATE.CLIMATE_MAX_RETRIES

        for attempt in range(max_retries + 1):
            try:
                response = self._session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                break

            except requests.RequestException as e:
                if attempt == max_retries:
                    raise ClimateServiceError(
                        f"Open-Meteo Indisponível após {max_retries} tentativas: {repr(e)}"
                    ) from e

                backoff = 2 ** attempt
                import time
                time.sleep(backoff)

        return self._normalize_daily_response(payload)

    def get_intraday_snapshot(
        self,
        latitude: float,
        longitude: float,
        reference_ts: datetime,
        window_hours: int = 3,
    ) -> Dict[str, float]:
        """
        Retorna um resumo intradiário (janela móvel em horas) para variar ciclos subdiários.

        Estratégia:
        - Busca série horária do dia de referência em UTC
        - Agrega os últimos `window_hours` horários <= reference_ts
        """
        if reference_ts.tzinfo is None:
            reference_ts = reference_ts.replace(tzinfo=timezone.utc)
        else:
            reference_ts = reference_ts.astimezone(timezone.utc)

        if window_hours <= 0:
            window_hours = 3

        ref_date = reference_ts.date()
        start_date = ref_date - timedelta(days=1)
        url = self._select_endpoint(ref_date)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "precipitation,temperature_2m,apparent_temperature",
            "timezone": "UTC",
            "start_date": start_date.isoformat(),
            "end_date": ref_date.isoformat(),
        }

        response = self._session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        hourly = payload.get("hourly") or {}

        times = hourly.get("time") or []
        precipitation = hourly.get("precipitation") or []
        temperature = hourly.get("temperature_2m") or []
        apparent_temperature = hourly.get("apparent_temperature") or []

        if not times:
            raise ClimateServiceError("Resposta horária sem timestamps.")

        rows = []
        for i, raw_ts in enumerate(times):
            try:
                ts = datetime.fromisoformat(str(raw_ts))
            except Exception:
                continue

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)

            rows.append(
                {
                    "ts": ts,
                    "precipitation": float(precipitation[i] or 0.0) if i < len(precipitation) else 0.0,
                    "temperature_2m": float(temperature[i] or 0.0) if i < len(temperature) else 0.0,
                    "apparent_temperature": float(apparent_temperature[i] or 0.0) if i < len(apparent_temperature) else 0.0,
                }
            )

        if not rows:
            raise ClimateServiceError("Não foi possível normalizar série horária.")

        end_ts = reference_ts.replace(minute=0, second=0, microsecond=0)
        selected_until_ref = [r for r in rows if r["ts"] <= end_ts]
        if not selected_until_ref:
            raise ClimateServiceError("Sem dados horários para a referência.")

        recent_window_start = end_ts - timedelta(hours=max(1, window_hours) - 1)
        recent_window = [r for r in selected_until_ref if recent_window_start <= r["ts"] <= end_ts]
        if not recent_window:
            recent_window = [selected_until_ref[-1]]

        rolling24_start = end_ts - timedelta(hours=23)
        rolling24_window = [r for r in selected_until_ref if rolling24_start <= r["ts"] <= end_ts]
        if not rolling24_window:
            rolling24_window = recent_window

        if not rolling24_window:
            raise ClimateServiceError("Sem dados horários para a janela de referência.")

        # Mantém unidade diária esperada pelo modelo para precipitação (mm/24h).
        precip_sum_24h = sum(r["precipitation"] for r in rolling24_window)
        # Para temperatura, usa janela curta para captar variação intradiária.
        temp_mean_recent = sum(r["temperature_2m"] for r in recent_window) / len(recent_window)
        app_temp_mean_recent = sum(r["apparent_temperature"] for r in recent_window) / len(recent_window)

        return {
            "precipitacao_total_mm": float(precip_sum_24h),
            "temperatura_media_2m_C": float(temp_mean_recent),
            "temperatura_aparente_media_2m_C": float(app_temp_mean_recent),
        }
    # -------------------------------------------------
    # AUXILIARES
    # -------------------------------------------------

    def _select_endpoint(self, reference_date: date) -> str:
        """
        Seleciona endpoint apropriado:
        - Archive para datas passadas
        - Forecast para hoje/futuro
        """
        today = date.today()

        if reference_date < today:
            return self.base_archive_url

        return self.base_forecast_url

    def _normalize_daily_response(self, payload: Dict) -> List[Dict]:
        """
        Normaliza estrutura retornada pela Open-Meteo.
        """

        if "daily" not in payload:
            raise ClimateServiceError("Resposta inválida da Open-Meteo")

        daily = payload["daily"]

        required_keys = [
            "time",
            "precipitation_sum",
            "temperature_2m_mean",
            "apparent_temperature_mean",
        ]

        for key in required_keys:
            if key not in daily:
                raise ClimateServiceError(
                    f"Campo ausente na resposta Open-Meteo: {key}"
                )

        series = []

        for i in range(len(daily["time"])):
            series.append(
                {
                    "date": date.fromisoformat(daily["time"][i]),
                    "precipitacao_total_mm": float(
                        daily["precipitation_sum"][i] or 0.0
                    ),
                    "temperatura_media_2m_C": float(
                        daily["temperature_2m_mean"][i] or 0.0
                    ),
                    "temperatura_aparente_media_2m_C": float(
                        daily["apparent_temperature_mean"][i] or 0.0
                    ),
                }
            )

        return series
