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
from backend.app.services.feature_builder import FeatureBuilder , FEATURE_ORDER
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
    
    def get_point_by_id(self, point_id: str) -> CriticalPoint:
        """
        Retorna um ponto crítico pelo ID (ex: p1, p2, ...)
        Usado pelo endpoint /map/points/{id}/risk
        """
        points = self.get_all_points()
        for p in points:
            if p.id == point_id:
                return p
        raise RiskOrchestrationError(f"Ponto não encontrado: {point_id}")
    
    def get_points_for_map(self, with_risk: bool = True) -> List[MapPointSchema]:
        """
        Retorna pontos para o mapa
        - with_risk=True: Calcula risco via IA 
        - with_risk=False: Retorna apenas os pontos com risco_atual=None
        """
        points = self.get_all_points()
        today = date.today()

        result: List[MapPointSchema] = []

        for point in points:
            if not with_risk:
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
                continue
            
            try:
                point_with_risk = self.evaluate_point_risk(
                    point=point,
                    target_date=today,
                    with_history=True,
                )
                result.append(point_with_risk)
            
            except Exception:
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

            HISTORY_DAYS = 90

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

            features = {k: features.get(k, 0.0) for k in FEATURE_ORDER}
            
            icra_result = self._call_icra_api(
                features=features,
                target_date=target_date,
                point_id=point.id,
                )

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
                nivel=self._normalize_risk_level(icra_result.get("nivel_risco", "")),
                confianca=icra_result.get("confianca", "Indefinida"),
                cor=self._map_risk_color(icra_result.get("nivel_risco", "")),
            )

            return MapPointSchema(
                ponto=point_schema,
                risco_atual=risk_schema,
            )

        except Exception as e:
            print("\n[ERRO - RISK ORCHESTRATOR]")
            print(f"Ponto: {point.id} | {point.nome}")
            print(f"Data alvo: {target_date}")
            print(f"Erro: {repr(e)}")
            raise RiskOrchestrationError(
                f"Erro ao avaliar risco do ponto '{point.nome}'"
            )
        
    def _normalize_risk_level(self, raw: str) -> str:
        """
        Normaliza o nível de risco retornado pela IA para o padrão do frontend.
        Aceita: "Alto", "alto", "muito_alto", "Muito Alto", "MUITO_ALTO", etc.
        Retorna: "Baixo" | "Moderado" | "Alto" | "Muito Alto"
        """
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
        return mapping.get(v, raw.strip().title())       

    def _map_risk_color(self, nivel: str) -> str:
        """
        Mapeia o nível de risco para uma cor semântica.
        """
        nivel = (nivel or "").lower().strip()

        nivel = nivel.replace("-", "_").replace(" ", "_")

        if nivel == "baixo":
            return "verde"

        if nivel == "moderado":
            return "amarelo"
        if nivel == "alto":
            return "vermelho"

        if nivel == "muito_alto":
            return "vermelho_escuro"

        return "cinza"


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

        print("\n[ICRA API CALL]")
        print(f"Payload enviado:", payload)
        print("Status code:", response.status_code)
        print("Resposta bruta:", response.text)

        if response.status_code != 200:
            raise RiskOrchestrationError(
                f"Erro na API ICRA ({response.status_code}): {response.text}"
            )

        return response.json()
