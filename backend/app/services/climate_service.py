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

from datetime import date
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
