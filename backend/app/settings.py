"""
settings.py

Configuração central do Backend Core do projeto ClimaGyn.

- Leitura via .env (Pydantic Settings v2)
- Suporte a ambientes (dev/staging/prod)
- Configuração de banco de dados (PostgreSQL)
- Configuração de scheduler de risco
- Configuração de provedores climáticos
- Configuração da API de IA (ICRA)

Este arquivo NÃO contém lógica de negócio.
"""

from pathlib import Path
from typing import Optional, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==========================================================
# ROOT DO PROJETO
# ==========================================================

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


# ==========================================================
# SETTINGS BASE (ENV)
# ==========================================================

class BaseAppSettings(BaseSettings):
    """
    Classe base para leitura de variáveis de ambiente.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# ==========================================================
# APLICAÇÃO
# ==========================================================

class AppSettings(BaseAppSettings):
    ENV: str = Field(default="development")  # development | staging | production
    NAME: str = Field(default="ClimaGyn Backend Core")
    VERSION: str = Field(default="2.0.0")

    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8001)

    LOG_LEVEL: str = Field(default="INFO")


# ==========================================================
# BANCO DE DADOS
# ==========================================================

class DatabaseSettings(BaseAppSettings):
    """
    Configuração do banco PostgreSQL.
    """

    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/climagyn"
    )

    POOL_SIZE: int = Field(default=5)
    MAX_OVERFLOW: int = Field(default=10)
    ECHO_SQL: bool = Field(default=False)


# ==========================================================
# API DE IA (ICRA)
# ==========================================================

class IASettings(BaseAppSettings):
    """
    Configurações para comunicação com a API de IA.
    """

    BASE_URL: str = Field(default="http://localhost:8501")
    PREDICT_ENDPOINT: str = Field(default="/icra/predict")
    HEALTH_ENDPOINT: str = Field(default="/health")

    TIMEOUT_SECONDS: int = Field(default=30)

    MODEL_NAME: str = Field(default="ICRA")
    MODEL_VERSION: str = Field(default="v1.0")


# ==========================================================
# PROVEDORES CLIMÁTICOS
# ==========================================================

class ClimateSettings(BaseAppSettings):
    """
    Configurações para integração com provedores climáticos.
    """

    # Open-Meteo
    OPEN_METEO_FORECAST_URL: str = Field(
        default="https://api.open-meteo.com/v1/forecast"
    )

    OPEN_METEO_ARCHIVE_URL: str = Field(
        default="https://archive-api.open-meteo.com/v1/archive"
    )

    CLIMATE_TIMEOUT_SECONDS: int = Field(default=20)
    CLIMATE_MAX_RETRIES: int = Field(default=2)

    # OpenWeather 
    OPEN_WEATHER_BASE_URL: str = Field(
        default="https://api.openweathermap.org/data/2.5"
    )

    OPEN_WEATHER_API_KEY: Optional[str] = Field(default=None)

    PRIMARY_PROVIDER: str = Field(default="open_meteo")
    FALLBACK_PROVIDER: Optional[str] = Field(default=None)


# ==========================================================
# RISCO / SNAPSHOT / SCHEDULER
# ==========================================================

class RiskSettings(BaseAppSettings):
    """
    Configurações relacionadas a snapshots e atualização automática.
    """
    SCHEDULE_INTERVAL_SECONDS: int = Field(default=10800)  
    SNAPSHOT_TTL_SECONDS: int = Field(default=10800)  
    SCHEDULER_ENABLED: bool = Field(default=True)
    FALLBACK_ON_DEMAND: bool = Field(default=True)
    HIGH_RISK_THRESHOLD: float = Field(default=0.7)

# ==========================================================
# MAPA / PONTOS
# ==========================================================

class MapSettings(BaseAppSettings):
    """
    Configurações espaciais.
    """

    MAX_POINTS: int = Field(default=120)
    DEFAULT_POINT_RADIUS_M: int = Field(default=300)

# ==========================================================
# CORS
# ==========================================================
class CORSSettings(BaseAppSettings):
    """
    Configurações de CORS para a API.
    """
    CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["*"],)
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["*"])


# ==========================================================
# DADOS DO PROJETO
# ==========================================================

class DataSettings(BaseAppSettings):
    """
    Configurações relacionadas a arquivos locais.
    """

    CRITICAL_POINTS_CSV_PATH: Optional[str] = Field(default=None)

    @property
    def CRITICAL_POINTS_CSV(self) -> Path:
        if self.CRITICAL_POINTS_CSV_PATH:
            return Path(self.CRITICAL_POINTS_CSV_PATH)

        return (
            PROJECT_ROOT
            / "backend"
            / "app"
            / "data"
            / "pontos_criticos.csv"
        )
    
# ==========================================================
# AGREGADOR FINAL
# ==========================================================

class Settings:
    """
    Agregador único de configurações.
    """

    APP = AppSettings()
    DATABASE = DatabaseSettings()
    IA = IASettings()
    CLIMATE = ClimateSettings()
    RISK = RiskSettings()
    MAP = MapSettings()
    DATA = DataSettings()
    CORS = CORSSettings()

    # ------------------------------
    # Aliases compatibilidade FastAPI
    # ------------------------------

    @property
    def APP_NAME(self) -> str:
        return self.APP.NAME

    @property
    def APP_VERSION(self) -> str:
        return self.APP.VERSION

    @property
    def APP_DESCRIPTION(self) -> str:
        return (
            "Backend central de orquestração climática e risco urbano "
            "do projeto ClimaGyn."
        )

    @property
    def DEBUG(self) -> bool:
        return self.APP.DEBUG
    
    @property
    def DATABASE_URL(self) -> str:
        return self.DATABASE.DATABASE_URL


# Instância global única
settings = Settings()
