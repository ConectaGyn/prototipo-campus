"""
climate_service.py

Serviço responsável por obter dados climáticos externos
(Open-Meteo, OpenWeather, etc.) e normalizá-los para uso
interno no backend.

Este módulo:
- NÃO calcula risco
- NÃO monta features
- NÃO conhece IA

Ele apenas fornece dados climáticos confiáveis.
"""

from typing import Dict, Optional
from datetime import date

import requests

from backend.app.settings import settings
from backend.app.utils.time_utils import today_utc


# ================================
# EXCEÇÕES
# ================================

class ClimateServiceError(Exception):
    """Erro genérico ao obter dados climáticos."""


# ================================
# SERVIÇO PRINCIPAL
# ================================

class ClimateService:
    """
    Serviço de integração com provedores climáticos.
    """

    def __init__(self):
        self.primary_provider = settings.CLIMATE.PRIMARY_PROVIDER
        self.daily_cache: dict = {}

    # -------------------------------------------------
    # API PÚBLICA
    # -------------------------------------------------

    def get_daily_climate(
        self,
        latitude: float,
        longitude: float,
        target_date: Optional[date] = None,
    ) -> Dict[str, float]:
        """
        Retorna dados climáticos agregados para um dia específico.

        Parâmetros
        ----------
        latitude : float
        longitude : float
        target_date : date, opcional
            Data de referência (default: hoje UTC)

        Retorno
        -------
        dict
            Dados climáticos normalizados
        """

        if target_date is None:
            target_date = today_utc()

        if self.primary_provider == "open_meteo":
            return self._fetch_open_meteo_daily(latitude, longitude, target_date)

        if self.primary_provider == "open_weather":
            return self._fetch_open_weather_daily(latitude, longitude, target_date)

        raise ClimateServiceError(
            f"Provedor climático não suportado: {self.primary_provider}"
        )

    # -------------------------------------------------
    # PROVEDORES
    # -------------------------------------------------

    def _fetch_open_meteo_daily(
        self,
        latitude: float,
        longitude: float,
        target_date: date,
    ) -> Dict[str, float]:
        """
        Busca dados diários no Open-Meteo.
        """

        try:
            cache_key = (latitude, longitude, target_date.isoformat())

            if cache_key in self.daily_cache:
                return self.daily_cache[cache_key]

            today = today_utc()

            if  target_date < today:
                url = "https://archive-api.open-meteo.com/v1/archive"
            else:
                url = "https://api.open-meteo.com/v1/forecast"

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": "precipitation_sum,temperature_2m_mean,apparent_temperature_mean",
                "timezone": "UTC",
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
            }

            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()

            data = response.json()

            result = {
                "precipitacao_total_mm": data["daily"]["precipitation_sum"][0],
                "temperatura_media_2m_C": data["daily"]["temperature_2m_mean"][0],
                "temperatura_aparente_media_2m_C": data["daily"][
                    "apparent_temperature_mean"
                ][0],
            }

            self.daily_cache[cache_key] = result
            return result

        except Exception as e:
            return {
                "precipitacao_total_mm": 0.0,
                "temperatura_media_2m_C": 0.0,
                "temperatura_aparente_media_2m_C": 0.0,
            }

    def _fetch_open_weather_daily(
        self,
        latitude: float,
        longitude: float,
        target_date: date,
    ) -> Dict[str, float]:
        """
        Fallback usando Open-Meteo quando OpenWeather não está disponível.
        """

        try:
            today = today_utc()

            if  target_date < today:
                url = "https://archive-api.open-meteo.com/v1/archive"
            else:
                url = "https://api.open-meteo.com/v1/forecast"

            params = {
                "lat": latitude,
                "lon": longitude,
                "daily": "precipitation_sum,temperature_2m_mean,apparent_temperature_mean",
                "timezone": "UTC",
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            return {
                "precipitacao_total_mm": data["daily"]["precipitation_sum"][0],
                "temperatura_media_2m_C": data["daily"]["temperature_2m_mean"][0],
                "temperatura_aparente_media_2m_C": data["daily"]["apparent_temperature_mean"][0],
            }

        except Exception as e:
            raise ClimateServiceError(
                f"Erro ao obter dados do OpenWeather: {e}"
            )
