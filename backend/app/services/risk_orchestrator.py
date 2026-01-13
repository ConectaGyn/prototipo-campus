"""
risk_orchestrator.py

Camada central de orquestração de risco do backend.
"""

from typing import Dict, List
from datetime import date, timedelta
from pathlib import Path
import csv
import requests


from backend.app.settings import settings
from backend.app.models.point import CriticalPoint, GeoLocation
from backend.app.services.climate_service import ClimateService
from backend.app.services.feature_builder import FeatureBuilder
from backend.app.schemas.map import MapPointSchema, RiskStatusSchema
from backend.app.schemas.point import PointResponse


# ================================
# EXCEÇÃO DE DOMÍNIO
# ================================

class RiskOrchestrationError(Exception):
    """Erro na orquestração de risco."""


# ================================
# ORQUESTRATOR
# ================================

class RiskOrchestrator:
    """
    Serviço central de cálculo de risco por ponto crítico.
    """

    def __init__(self):
        self.climate_service = ClimateService()
        self.feature_builder = FeatureBuilder()
        self._points_cache: List[CriticalPoint] | None = None

    # -------------------------------------------------
    # CARREGAMENTO DE PONTOS (CSV)
    # -------------------------------------------------

    def _load_points_from_csv(self) -> List[CriticalPoint]:
        """
        Carrega os pontos críticos a partir do CSV oficial do projeto.
        Espera colunas: local, latitude, longitude
        """

        csv_path = settings.DATA.CRITICAL_POINTS_CSV

        if not csv_path.exists():
            raise RiskOrchestrationError(
                f"Arquivo de pontos críticos não encontrado: {csv_path}"
            )

        points: List[CriticalPoint] = []

        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader, start=1):
                points.append(
                    CriticalPoint(
                        id=f"p{idx}",
                        nome=row["local"],
                        localizacao=GeoLocation(
                            latitude=float(row["latitude"]),
                            longitude=float(row["longitude"]),
                        ),
                        bairro=None,
                        descricao=None,
                        ativo=True,
                    )
                )

        return points

    def get_all_points(self) -> List[CriticalPoint]:
        """
        Retorna todos os pontos críticos monitorados.
        Usa cache em memória para evitar releitura do CSV.
        """
        if self._points_cache is None:
            self._points_cache = self._load_points_from_csv()
        return self._points_cache
    
    def get_points_for_map(self) -> List[MapPointSchema]:
        """
        Retorna pontos prontos para mapa, sem cálculo de risco.
        """
        points = self.get_all_points()

        result = []
        for point in points:
            result.append(
            MapPointSchema(
                ponto=PointResponse(
                    id=point.id,
                    nome=point.nome,
                    localizacao={
                        "latitude": point.localizacao.latitude,
                        "longitude": point.localizacao.longitude,
                    },
                    ativo=point.ativo,
                    raio_influencia_m=point.raio_influencia_m,
                    bairro=point.bairro,
                    descricao=point.descricao,
                ),
                risco_atual=None,
            )
        )

        return result


    # -------------------------------------------------
    # AVALIAÇÃO DE RISCO POR PONTO
    # -------------------------------------------------

    def evaluate_point_risk(
        self,
        point: CriticalPoint,
        target_date: date,
        with_history: bool = True,
    ) -> MapPointSchema:
        """
        Avalia o risco climático de um ponto crítico.
        """

        try:
            climate_today = self.climate_service.get_daily_climate(
                latitude=point.localizacao.latitude,
                longitude=point.localizacao.longitude,
                target_date=target_date,
            )

            HISTORY_DAYS = 30

            precip_series: List[float] = []
            temp_series: List[float] = []

            if with_history:
                for i in range(1, HISTORY_DAYS + 1):
                    past_date = target_date - timedelta(days=i)
                    past_climate = self.climate_service.get_daily_climate(
                        latitude=point.localizacao.latitude,
                        longitude=point.localizacao.longitude,
                        target_date=past_date,
                    )
                    
                    precip_series.append(past_climate["precipitacao_total_mm"])
                    temp_series.append(past_climate["temperatura_media_2m_C"])

            climate_history = {
                "precipitacao_total_mm": precip_series,
                "temperatura_media_2m_C": temp_series,
            }

            features = self.feature_builder.build_features(
                climate_today=climate_today,
                climate_history=climate_history,
                target_date=target_date,
            )

            try:
                icra_result = self._call_icra_api(
                    features=features,
                    target_date=target_date,
                    point_id=point.id,
            )

            except Exception:
                icra_result = {
                    "icra": -1.0,
                    "nivel_risco": "Indisponível",
                    "confianca": "Baixa",
                    "cor": "cinza",
                }

            point_schema = PointResponse(
                id=point.id,
                nome=point.nome,
                localizacao={
                    "latitude": point.localizacao.latitude,
                    "longitude": point.localizacao.longitude,
                },
                ativo=point.ativo,
                raio_influencia_m=point.raio_influencia_m,
                bairro=point.bairro,
                descricao=point.descricao,
            )

            risk_schema = RiskStatusSchema(
                icra=icra_result["icra"],
                nivel=icra_result["nivel_risco"],
                confianca=icra_result["confianca"],
                cor=icra_result.get("cor", "cinza"),
            )

            return MapPointSchema(
                ponto=point_schema,
                risco_atual=risk_schema,
            )

        except Exception as e:
            raise RiskOrchestrationError(
                f"Erro ao avaliar risco do ponto '{point.nome}': {e}"
            )

    # -------------------------------------------------
    # CHAMADA DA API ICRA
    # -------------------------------------------------

    def _call_icra_api(
        self,
        features: Dict[str, float],
        target_date: date,
        point_id: str,
    ) -> Dict:
        """
        Chama a API de IA (ICRA) para inferência.
        """

        payload = {
            "data": target_date.isoformat(),
            "features": features,
            "ponto": point_id,
        }

        response = requests.post(
            settings.IA.BASE_URL + settings.IA.PREDICT_ENDPOINT,
            json=payload,
            timeout=settings.IA.TIMEOUT,
        )

        if response.status_code != 200:
            raise RiskOrchestrationError(
                f"Erro na API ICRA ({response.status_code}): {response.text}"
            )

        return response.json()
