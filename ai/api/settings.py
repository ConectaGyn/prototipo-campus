"""
settings.py

Configurações centrais da API de inferência ICRA.
Arquivo de contrato global da aplicação.
"""

from pathlib import Path


# =====================================================
# RAIZ DO PROJETO (ÚNICA FONTE DE VERDADE)
# =====================================================

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


# =====================================================
# CONFIGURAÇÕES DO MODELO ICRA
# =====================================================

class ModelSettings:
    """
    Configurações relacionadas exclusivamente ao modelo ICRA.
    """

    VERSION: str = "v1"

    MODELS_DIR: Path = PROJECT_ROOT / "ai" / "models" / "icra"

    MODEL_PATH: Path = MODELS_DIR / f"icra_model_{VERSION}.joblib"
    THRESHOLDS_PATH: Path = MODELS_DIR / f"icra_thresholds_{VERSION}.json"
    FEATURES_PATH: Path = MODELS_DIR / f"icra_features_{VERSION}.json"


# =====================================================
# CONFIGURAÇÕES GERAIS DA APLICAÇÃO
# =====================================================

class Settings:
    """
    Configurações globais da aplicação.
    """

    # -------------------------------
    # API
    # -------------------------------
    APP_NAME: str = "ICRA Risk Prediction API"
    APP_DESCRIPTION: str = (
        "API de inferência do índice ICRA para risco climático e alagamentos."
    )
    APP_VERSION: str = "1.0.0"

    DEBUG: bool = False
    PORT: int = 8000

    # -------------------------------
    # MODELO (IMUTÁVEL)
    # -------------------------------
    MODEL: ModelSettings = ModelSettings()


# =====================================================
# SINGLETON
# =====================================================

settings = Settings()
