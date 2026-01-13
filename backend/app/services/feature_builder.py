"""
feature_builder.py

Responsável por construir o vetor de features utilizado pelo
modelo ICRA a partir de dados climáticos atuais e históricos.

Este módulo:
- NÃO executa inferência
- NÃO classifica risco
- NÃO acessa APIs externas diretamente

Ele apenas transforma dados em features numéricas.
"""

from typing import Dict, List
from datetime import date
import math


# ================================
# CONTRATO DE FEATURES (ORDEM!)
# ================================

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


# ================================
# EXCEÇÕES
# ================================

class FeatureBuilderError(Exception):
    """Erro na construção das features."""


# ================================
# FEATURE BUILDER
# ================================

class FeatureBuilder:
    """
    Constrói as features do modelo ICRA.
    """

    # -------------------------------------------------
    # API PÚBLICA
    # -------------------------------------------------

    def build_features(
        self,
        climate_today: Dict[str, float],
        climate_history: Dict[str, List[float]],
        target_date: date,
    ) -> Dict[str, float]:
        """
        Constrói todas as features necessárias para inferência.

        Parâmetros
        ----------
        climate_today : dict
            Dados climáticos do dia atual
        climate_history : dict
            Séries históricas (listas ordenadas por tempo)
        target_date : date
            Data da previsão

        Retorno
        -------
        dict
            Dicionário com todas as features
        """

        try:
            features = {}

            # ==========================
            # BASE DIRETA
            # ==========================
            features["precipitacao_total_mm"] = climate_today["precipitacao_total_mm"]
            features["temperatura_media_2m_C"] = climate_today["temperatura_media_2m_C"]
            features["temperatura_aparente_media_2m_C"] = climate_today[
                "temperatura_aparente_media_2m_C"
            ]

            # ==========================
            # MÉDIAS MÓVEIS
            # ==========================
            precip_series = climate_history["precipitacao_total_mm"]

            features["precipitacao_ma_7d"] = self.safe_mean(
                precip_series, 7)
            features["precipitacao_ma_30d"] = self.safe_mean(
                precip_series, 30
            )
            features["precipitacao_ma_90d"] = self.safe_mean(
                precip_series, 90
            )

            # ==========================
            # ANOMALIAS
            # ==========================
            features["anomalia_precip_7d"] = (
                features["precipitacao_total_mm"]
                - features["precipitacao_ma_7d"]
            )
            features["anomalia_precip_30d"] = (
                features["precipitacao_total_mm"]
                - features["precipitacao_ma_30d"]
            )

            # ==========================
            # INTENSIDADE
            # ==========================
            features["intensidade_precipitacao"] = (
                features["precipitacao_total_mm"] / max(1.0, 24.0)
            )

            # ==========================
            # LAGS DE PRECIPITAÇÃO
            # ==========================
            features["precipitacao_lag_1d"] = self._safe_lag(precip_series, 1)
            features["precipitacao_lag_2d"] = self._safe_lag(precip_series, 2)
            features["precipitacao_lag_3d"] = self._safe_lag(precip_series, 3)
            features["precipitacao_lag_7d"] = self._safe_lag(precip_series, 7)
            features["precipitacao_lag_14d"] = self._safe_lag(precip_series, 14)
            features["precipitacao_lag_30d"] = self._safe_lag(precip_series, 30)
    
            # ==========================
            # LAGS DE TEMPERATURA
            # ==========================
            temp_serie = climate_history["temperatura_media_2m_C"]

            features["temperatura_lag_1d"] = self._safe_lag(temp_serie, 1)
            features["temperatura_lag_7d"] = self._safe_lag(temp_serie, 7)

            # ==========================
            # COMPONENTES SAZONAIS
            # ==========================
            features.update(self._seasonal_components(target_date))

            # ==========================
            # VALIDAÇÃO FINAL
            # ==========================
            self._validate(features)

            return features

        except Exception as e:
            raise FeatureBuilderError(f"Erro ao construir features: {e}")

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------

    def _mean(self, series: List[float], window: int) -> float:
        if len(series) < window:
            raise FeatureBuilderError(
                f"Histórico insuficiente para média móvel de {window} dias"
            )
        return sum(series[-window:]) / window
    
    def _safe_mean(self, series: List[float], window: int) -> float:
        if not series:
            return 0.0
        if len(series) < window:
            return sum(series) / len(series)
        return sum(series[-window:]) / window

    def _safe_lag(self, series: List[float], window: int) -> float:
        if not series:
            return 0.0
        if len(series) < window:
            return sum(series) / len(series)
        return sum(series[-window:]) / window

    def _seasonal_components(self, d: date) -> Dict[str, float]:
        """
        Calcula componentes seno/cosseno de mês e dia.
        """

        mes = d.month
        dia_ano = d.timetuple().tm_yday

        return {
            "mes_sin": math.sin(2 * math.pi * mes / 12),
            "mes_cos": math.cos(2 * math.pi * mes / 12),
            "dia_sin": math.sin(2 * math.pi * dia_ano / 365),
            "dia_cos": math.cos(2 * math.pi * dia_ano / 365),
        }

    def _validate(self, features: Dict[str, float]) -> None:
        """
        Garante que todas as features exigidas existem.
        """

        missing = [f for f in FEATURE_ORDER if f not in features]
        if missing:
            raise FeatureBuilderError(
                f"Features ausentes após construção: {missing}"
            )
