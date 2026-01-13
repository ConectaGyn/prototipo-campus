"""
model_loader.py

Carregamento centralizado dos artefatos do modelo ICRA.
Responsável por garantir que modelo, thresholds e features
estejam disponíveis em formato consistente para a API.
"""

import json
from typing import List, Dict
from pathlib import Path

import joblib

from ai.api.settings import settings


# =====================================================
# CONTAINER
# =====================================================

class ModelArtifacts:
    def __init__(self):
        self.model = None
        self.thresholds: Dict[str, float] | None = None
        self.features: List[str] | None = None


_artifacts = ModelArtifacts()


# =====================================================
# LOADERS INTERNOS
# =====================================================

def _validate_path(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} não encontrado em: {path}")
    return path


def _load_model() -> None:
    path = _validate_path(settings.MODEL.MODEL_PATH, "Modelo ICRA")
    _artifacts.model = joblib.load(path)


def _load_thresholds() -> None:
    path = _validate_path(settings.MODEL.THRESHOLDS_PATH, "Thresholds ICRA")
    with open(path, "r", encoding="utf-8") as f:
        _artifacts.thresholds = json.load(f)


def _load_features() -> None:
    """
    Carrega e normaliza a lista de features utilizadas pelo modelo.

    O arquivo JSON pode conter metadados adicionais, mas este loader
    garante que apenas a lista ordenada de features seja exposta.
    """
    path = _validate_path(settings.MODEL.FEATURES_PATH, "Features ICRA")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Caso o JSON contenha metadados (formato esperado)
    if isinstance(data, dict):
        if "features" not in data:
            raise ValueError(
                "Arquivo de features inválido: chave 'features' não encontrada."
            )
        features = data["features"]
    else:
        # Caso raro: JSON seja apenas uma lista
        features = data

    if not isinstance(features, list) or not all(isinstance(f, str) for f in features):
        raise ValueError("Lista de features inválida no arquivo de configuração.")

    _artifacts.features = features


# =====================================================
# API PÚBLICA
# =====================================================

def load_artifacts() -> None:
    """
    Carrega todos os artefatos do modelo ICRA.

    Deve ser chamado uma única vez na inicialização da aplicação.
    """
    if _artifacts.model is None:
        _load_model()

    if _artifacts.thresholds is None:
        _load_thresholds()

    if _artifacts.features is None:
        _load_features()


def get_icra_model():
    if _artifacts.model is None:
        raise RuntimeError("Modelo ICRA ainda não carregado.")
    return _artifacts.model


def get_icra_thresholds() -> Dict[str, float]:
    if _artifacts.thresholds is None:
        raise RuntimeError("Thresholds ICRA ainda não carregados.")
    return _artifacts.thresholds


def get_icra_features() -> List[str]:
    if _artifacts.features is None:
        raise RuntimeError("Features ICRA ainda não carregadas.")
    return _artifacts.features
