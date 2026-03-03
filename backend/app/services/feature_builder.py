"""
feature_builder.py

Responsável por construir o vetor de features utilizado pelo
modelo ICRA a partir de uma série climática diária completa.

Este módulo:
- NÃO executa inferência
- NÃO acessa APIs externas
- NÃO salva dados

Ele apenas transforma séries climáticas em features numéricas.
"""

from typing import Dict, List
from datetime import date
import math


# =====================================================
# CONTRATO FORMAL DE FEATURES (ORDEM DO MODELO)
# =====================================================

FEATURE_ORDER: List[str] = [
    "precipitacao_total_mm",
    "precipitacao_ma_7d",
    "precipitacao_ma_30d",
    "precipitacao_ma_90d",
    "anomalia_precip_7d",
    "anomalia_precip_30d",
    "intensidade_precipitacao",
    "precipitacao_lag_1d",
    "precipitacao_lag_2d",
    "precipitacao_lag_3d",
    "precipitacao_lag_7d",
    "precipitacao_lag_14d",
    "precipitacao_lag_30d",
    "temperatura_media_2m_C",
    "temperatura_aparente_media_2m_C",
    "temperatura_lag_1d",
    "temperatura_lag_7d",
    "mes_sin",
    "mes_cos",
    "dia_sin",
    "dia_cos",
]


# =====================================================
# EXCEÇÃO
# =====================================================

class FeatureBuilderError(Exception):
    """Erro na construção das features."""


# =====================================================
# FEATURE BUILDER
# =====================================================

class FeatureBuilder:
    """
    Constrói as features do modelo ICRA a partir de
    uma série diária ordenada cronologicamente.
    """

    # -------------------------------------------------
    # API PÚBLICA
    # -------------------------------------------------

    def build_features(
        self,
        climate_today: Dict[str, float],
        climate_history: List[Dict[str, float]],
        target_date: date,
    ) -> Dict[str, float]:
        """
        Constrói features a partir de:
        - climate_today: dict com valores do dia atual
        - climate_history: dict com listas históricas (index 0 = ontem)
        """

        try:
            precip_series = climate_history.get("precipitacao_total_mm", [])
            temp_series = climate_history.get("temperatura_media_2m_C", [])

            features: Dict[str, float] = {}

            # =================================================
            # BASE DIRETA
            # =================================================

            features["precipitacao_total_mm"] = float(
                climate_today.get("precipitacao_total_mm", 0.0)
            )

            features["temperatura_media_2m_C"] = float(
                climate_today.get("temperatura_media_2m_C", 0.0)
            )

            features["temperatura_aparente_media_2m_C"] = float(
                climate_today.get("temperatura_aparente_media_2m_C", 0.0)
            )

            # =================================================
            # MÉDIAS MÓVEIS
            # =================================================

            features["precipitacao_ma_7d"] = self._moving_average(precip_series, 7)
            features["precipitacao_ma_30d"] = self._moving_average(precip_series, 30)
            features["precipitacao_ma_90d"] = self._moving_average(precip_series, 90)

            # =================================================
            # ANOMALIAS
            # =================================================

            features["anomalia_precip_7d"] = (
                features["precipitacao_total_mm"]
                - features["precipitacao_ma_7d"]
            )

            features["anomalia_precip_30d"] = (
                features["precipitacao_total_mm"]
                - features["precipitacao_ma_30d"]
            )

            # =================================================
            # INTENSIDADE
            # =================================================

            media_7d = features["precipitacao_ma_7d"]

            if media_7d > 0:
                features["intensidade_precipitacao"] = (
                    features["precipitacao_total_mm"] / media_7d
                )
            else:
                features["intensidade_precipitacao"] = 0.0

            # =================================================
            # LAGS DE PRECIPITAÇÃO
            # =================================================

            features["precipitacao_lag_1d"] = self._lag(precip_series, 1)
            features["precipitacao_lag_2d"] = self._lag(precip_series, 2)
            features["precipitacao_lag_3d"] = self._lag(precip_series, 3)
            features["precipitacao_lag_7d"] = self._lag(precip_series, 7)
            features["precipitacao_lag_14d"] = self._lag(precip_series, 14)
            features["precipitacao_lag_30d"] = self._lag(precip_series, 30)

            # =================================================
            # LAGS DE TEMPERATURA
            # =================================================

            features["temperatura_lag_1d"] = self._lag(temp_series, 1)
            features["temperatura_lag_7d"] = self._lag(temp_series, 7)

            # =================================================
            # COMPONENTES SAZONAIS
            # =================================================

            features.update(self._seasonal_components(target_date))

            # =================================================
            # VALIDAÇÃO FINAL
            # =================================================

            self._validate(features)

            return features

        except Exception as e:
            raise FeatureBuilderError(
                f"Erro ao construir features (data={target_date}): {e}"
            )

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------

    def _moving_average(self, series: List[float], window: int) -> float:
        if not series:
            return 0.0

        if len(series) < window:
            return sum(series) / len(series)

        return sum(series[-window:]) / window

    def _lag(self, series: List[float], lag: int) -> float:
        if not series:
            return 0.0

        if len(series) < lag:
            return series[-1]

        return series[-lag]

    def _seasonal_components(self, d: date) -> Dict[str, float]:
        mes = d.month
        dia_ano = d.timetuple().tm_yday

        return {
            "mes_sin": math.sin(2 * math.pi * mes / 12),
            "mes_cos": math.cos(2 * math.pi * mes / 12),
            "dia_sin": math.sin(2 * math.pi * dia_ano / 365),
            "dia_cos": math.cos(2 * math.pi * dia_ano / 365),
        }

    def _validate(self, features: Dict[str, float]) -> None:
        missing = [f for f in FEATURE_ORDER if f not in features]

        if missing:
            raise FeatureBuilderError(
                f"Features faltando: {', '.join(missing)}"
            )
