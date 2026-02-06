"""
icra_service.py

Serviço responsável por executar inferência do modelo ICRA
e construir a resposta de risco para a API.
"""

import numpy as np

from ai.api.loaders.model_loader import (
    get_icra_model,
    get_icra_features,
    get_icra_thresholds,
)
from ai.api.utils.risk_utils import (
    classificar_nivel_risco,
    classificar_confianca,
)
from ai.api.schemas import (
    ICRAPredictRequest,
    ICRAPredictResponse,
    ICRADetails,
)


# ================================
# SERVIÇO PRINCIPAL
# ================================

def predict_icra(payload: ICRAPredictRequest) -> ICRAPredictResponse:
    """
    Executa a predição do índice ICRA a partir das features fornecidas.
    """

    # =====================================================
    # CARREGAR ARTEFATOS
    # =====================================================

    model = get_icra_model()
    features_esperadas = get_icra_features()
    thresholds = get_icra_thresholds()

    # =====================================================
    # MONTAR VETOR DE FEATURES (ORDEM GARANTIDA)
    # =====================================================

    try:
        X = np.array(
            [
                getattr(payload.features, feature)
                for feature in features_esperadas
            ],
            dtype=float
        ).reshape(1, -1)

    except AttributeError as e:
        raise ValueError(
            f"Feature ausente ou inválida no payload: {e}"
        )

    except Exception as e:
        raise ValueError(
            f"Erro ao montar vetor de features para inferência: {e}"
        )

    # =====================================================
    # PREDIÇÃO
    # =====================================================

    icra_pred = float(model.predict(X)[0])

    # =====================================================
    # INCERTEZA (SE DISPONÍVEL)
    # =====================================================

    icra_std = None
    if hasattr(model, "estimators_"):
        preds = np.array(
            [est.predict(X)[0] for est in model.estimators_],
            dtype=float
        )
        icra_std = float(preds.std())

    # =====================================================
    # CLASSIFICAÇÕES
    # =====================================================

    nivel_risco = classificar_nivel_risco(
        icra_value=icra_pred,
        thresholds=thresholds
    )

    confianca = classificar_confianca(
        icra_std=icra_std if icra_std is not None else 0.0
    )

    # =====================================================
    # DETALHES EXPLICATIVOS
    # =====================================================

    detalhes = ICRADetails(
        chuva_dia=payload.features.precipitacao_total_mm,
        chuva_30d=payload.features.precipitacao_ma_30d,
        chuva_90d=payload.features.precipitacao_ma_90d,
    )

    # =====================================================
    # RESPOSTA FINAL
    # =====================================================

    return ICRAPredictResponse(
        data=payload.data,
        icra=round(icra_pred, 3),
        icra_std=round(icra_std, 3) if icra_std is not None else None,
        nivel_risco=nivel_risco,
        confianca=confianca,
        detalhes=detalhes,
    )
