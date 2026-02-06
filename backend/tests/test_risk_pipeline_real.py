"""
test_risk_pipeline_real.py

Teste de integração real do pipeline de risco do ClimaGyn.

Este teste executa, para um subconjunto de pontos críticos reais:
- leitura do CSV real
- coleta climática real (ClimateService)
- construção real de features (FeatureBuilder)
- chamada real da API de IA (ICRA)
- montagem final do MapPointSchema

Objetivo:
Identificar exatamente em qual etapa o risco deixa de ser calculado
quando dados reais são utilizados.

IMPORTANTE:
- NÃO usa dados simulados
- NÃO depende de FastAPI
- NÃO usa frontend
"""

from datetime import date
from pprint import pprint
import sys
import traceback

from backend.app.settings import settings
from backend.app.services.climate_service import ClimateService
from backend.app.services.feature_builder import FeatureBuilder, FEATURE_ORDER
from backend.app.services.risk_orchestrator import RiskOrchestrator, RiskOrchestrationError


# =====================================================
# CONFIGURAÇÕES DO TESTE
# =====================================================

MAX_POINTS_TO_TEST = 3
TARGET_DATE = date.today()


# =====================================================
# HELPERS DE LOG
# =====================================================

def section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def subsection(title: str):
    print("\n--- " + title + " ---")


def log_ok(message: str):
    print(f"[OK] {message}")


def log_info(message: str):
    print(f"[INFO] {message}")


def log_error(message: str):
    print(f"[ERROR] {message}")


# =====================================================
# TESTE PRINCIPAL
# =====================================================

def main():
    section("INICIO DO TESTE DE PIPELINE REAL DE RISCO")

    print("Data alvo:", TARGET_DATE.isoformat())
    print("CSV de pontos:", settings.DATA.CRITICAL_POINTS_CSV)
    print("IA endpoint:", settings.IA.BASE_URL + settings.IA.PREDICT_ENDPOINT)

    orchestrator = RiskOrchestrator()
    climate_service = ClimateService()
    feature_builder = FeatureBuilder()

    # -------------------------------------------------
    # 1. CARREGAMENTO DOS PONTOS REAIS
    # -------------------------------------------------

    section("CARREGAMENTO DOS PONTOS CRITICOS")

    try:
        points = orchestrator.get_all_points()
        log_ok(f"{len(points)} pontos carregados do CSV")
    except Exception as e:
        log_error("Falha ao carregar pontos do CSV")
        raise

    if not points:
        log_error("Nenhum ponto encontrado no CSV")
        return

    points_to_test = points[:MAX_POINTS_TO_TEST]
    log_info(f"Testando apenas os primeiros {len(points_to_test)} pontos")

    # -------------------------------------------------
    # 2. LOOP PRINCIPAL DE TESTE
    # -------------------------------------------------

    for idx, point in enumerate(points_to_test, start=1):
        section(f"TESTE DO PONTO {idx}: {point.id} - {point.nome}")

        print("Coordenadas:", point.localizacao.latitude, point.localizacao.longitude)

        try:
            # ---------------------------------------------
            # 2.1 CLIMATE SERVICE - DIA ATUAL
            # ---------------------------------------------
            subsection("CLIMATE SERVICE - DIA ATUAL")

            climate_today = climate_service.get_daily_climate(
                latitude=point.localizacao.latitude,
                longitude=point.localizacao.longitude,
                target_date=TARGET_DATE,
            )

            log_ok("Dados climáticos do dia obtidos")
            pprint(climate_today)

            # ---------------------------------------------
            # 2.2 CLIMATE SERVICE - HISTORICO
            # ---------------------------------------------
            subsection("CLIMATE SERVICE - HISTORICO")

            precip_series = []
            temp_series = []

            for i in range(1, 31):
                past_date = TARGET_DATE.fromordinal(TARGET_DATE.toordinal() - i)
                past = climate_service.get_daily_climate(
                    latitude=point.localizacao.latitude,
                    longitude=point.localizacao.longitude,
                    target_date=past_date,
                )
                precip_series.append(past.get("precipitacao_total_mm", 0.0))
                temp_series.append(past.get("temperatura_media_2m_C", 0.0))

            log_ok(f"Historico coletado: {len(precip_series)} dias")

            climate_history = {
                "precipitacao_total_mm": precip_series,
                "temperatura_media_2m_C": temp_series,
            }

            # ---------------------------------------------
            # 2.3 FEATURE BUILDER
            # ---------------------------------------------
            subsection("FEATURE BUILDER")

            features = feature_builder.build_features(
                climate_today=climate_today,
                climate_history=climate_history,
                target_date=TARGET_DATE,
            )

            log_ok(f"{len(features)} features geradas")

            missing = [f for f in FEATURE_ORDER if f not in features]
            if missing:
                log_error(f"Features ausentes: {missing}")
            else:
                log_ok("Todas as features exigidas estão presentes")

            zero_features = [k for k, v in features.items() if v == 0]
            log_info(f"Features com valor zero: {zero_features}")

            # Força alinhamento exato com FEATURE_ORDER
            ordered_features = {k: features.get(k, 0.0) for k in FEATURE_ORDER}

            # ---------------------------------------------
            # 2.4 PAYLOAD PARA A IA
            # ---------------------------------------------
            subsection("PAYLOAD ICRA")

            payload = {
                "data": TARGET_DATE.isoformat(),
                "ponto": point.id,
                "features": ordered_features,
            }

            log_ok("Payload construído")
            pprint(payload)

            # ---------------------------------------------
            # 2.5 CHAMADA DA API DE IA
            # ---------------------------------------------
            subsection("CHAMADA DA API ICRA")

            icra_response = orchestrator._call_icra_api(
                features=ordered_features,
                target_date=TARGET_DATE,
                point_id=point.id,
            )

            log_ok("Resposta da IA recebida")
            pprint(icra_response)

            # ---------------------------------------------
            # 2.6 INTERPRETAÇÃO DO RISCO
            # ---------------------------------------------
            subsection("INTERPRETACAO DO RISCO")

            nivel = icra_response.get("nivel_risco")
            icra = icra_response.get("icra")

            if nivel is None:
                log_error("nivel_risco ausente na resposta da IA")
            else:
                log_ok(f"Nivel de risco: {nivel}")

            if icra is None:
                log_error("icra ausente na resposta da IA")
            else:
                log_ok(f"ICRA: {icra}")

            log_ok("Pipeline completo para este ponto")

        except RiskOrchestrationError as e:
            log_error("Erro de orquestração")
            print(str(e))

        except Exception as e:
            log_error("Erro inesperado durante o teste")
            traceback.print_exc()


    # -------------------------------------------------
    # FIM
    # -------------------------------------------------

    section("FIM DO TESTE DE PIPELINE REAL")
    print("Teste concluído")


# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nFalha crítica durante a execução do teste")
        traceback.print_exc()
        sys.exit(1)
