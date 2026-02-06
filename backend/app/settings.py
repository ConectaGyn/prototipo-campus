"""
settings.py

Configurações globais do Backend Core do projeto.

Este arquivo centraliza:
- Identidade da aplicação
- Integração com a API de IA (ICRA)
- Configurações de provedores climáticos
- Parâmetros operacionais do backend

Não contém lógica de negócio.
Não realiza chamadas externas.
"""

from pathlib import Path
from typing import Optional


PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


# =====================================================
# CONFIGURAÇÕES DA APLICAÇÃO
# =====================================================

class AppSettings:
    """
    Identidade e parâmetros gerais do backend.
    """

    NAME: str = "ClimaGyn Backend Core"
    VERSION: str = "1.0.0"

    DEBUG: bool = True
    PORT: int = 8001


# =====================================================
# CONFIGURAÇÕES DA API DE IA (ICRA)
# =====================================================

class IAServiceSettings:
    """
    Configurações para comunicação com a API de IA (ICRA).
    """

    # URL base da API de inferência
    BASE_URL: str = "http://localhost:8501"

    # Endpoints
    PREDICT_ENDPOINT: str = "/icra/predict"
    HEALTH_ENDPOINT: str = "/health"

    # Timeout padrão (segundos)
    TIMEOUT: int = 30

    #Identidade do modelo utilizado
    MODEL_NAME: str = "ICRA"
    MODEL_VERSION: str = "v1.0"

    FEATURES_SOURCE = "FeatureBuilder.FEATURE_ORDER"



# =====================================================
# CONFIGURAÇÕES CLIMÁTICAS
# =====================================================

class ClimateSettings:
    """
    Configurações relacionadas a provedores climáticos.
    """

    # -------------------------------
    # Open-Meteo (principal)
    # -------------------------------
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"

    # -------------------------------
    # OpenWeather (fallback)
    # -------------------------------
    OPEN_WEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"
    OPEN_WEATHER_API_KEY: Optional[str] = None  

    # -------------------------------
    # Estratégia
    # -------------------------------
    PRIMARY_PROVIDER: str = "open_meteo"
    FALLBACK_PROVIDER: str = "open_weather"


# =====================================================
# CONFIGURAÇÕES DE MAPA E PONTOS
# =====================================================

class MapSettings:
    """
    Parâmetros relacionados à visualização espacial.
    """

    # Quantidade máxima de pontos críticos carregados
    MAX_POINTS: int = 120

    # Raio padrão de influência do ponto (metros)
    DEFAULT_POINT_RADIUS_M: int = 300

# =====================================================
# CONFIGURAÇÕES DE DADOS DO PROJETO
# =====================================================

class DataSettings:
    """
    Configurações relacionadas a arquivos de dados do projeto
    (ex: pontos críticos).
    """

    DATA_DIR: Path = PROJECT_ROOT / "ai" / "data"
    CRITICAL_POINTS_CSV: Path = DATA_DIR / "metadata" / "pontos_criticos.csv"

class Settings:
    """
    Agregador único de configurações do backend.
    """

    APP = AppSettings()
    IA = IAServiceSettings()
    CLIMATE = ClimateSettings()
    MAP = MapSettings()
    DATA = DataSettings()

    # -------------------------------------------------
    # Aliases de compatibilidade (main.py / FastAPI)
    # -------------------------------------------------

    @property
    def APP_NAME(self) -> str:
        return self.APP.NAME

    @property
    def APP_DESCRIPTION(self) -> str:
        return (
            "Backend central de orquestração climática e risco urbano "
            "do projeto ClimaGyn."
        )

    @property
    def APP_VERSION(self) -> str:
        return self.APP.VERSION

    @property
    def DEBUG(self) -> bool:
        return self.APP.DEBUG


settings = Settings()

