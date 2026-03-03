import pytest
from datetime import datetime
from math import isclose

from backend.app.tests.utils.http_client import client

EPS = 1e-6

def _print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def _assert_between(value, low, high, label):
    assert low <= value <= high, (
        f"\n❌ {label} fora do intervalo esperado "
        f"[{low}, {high}]. Recebido: {value}"
    )


@pytest.mark.order(60)
class TestAnalyticsMetrics:

    MUNICIPALITY_ID = 1

    # =====================================================
    # SETUP — garantir que surface existe
    # =====================================================
    def _ensure_surface_exists(self):
        r = client.get(f"/surface/{self.MUNICIPALITY_ID}")
        assert r.status_code == 200, (
            "\nSurface precisa existir antes do teste Analytics.\n"
            f"Status: {r.status_code}\n"
            f"Body: {r.text}"
        )

    # =====================================================
    # 01 - CONTRATO DA API (estrutura)
    # =====================================================
    def test_01_current_metrics_structure(self):
        _print_header("TEST 06.01 — Contrato da API (estrutura)")

        self._ensure_surface_exists()

        response = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics"
        )

        assert response.status_code == 200, response.text
        data = response.json()

        for field in [
            "municipality",
            "surface",
            "high_risk_threshold",
            "surface_summary",
            "territorial_metrics",
        ]:
            assert field in data, f"\n❌ Campo ausente: {field}"

        summary = data["surface_summary"]
        for field in [
            "total_area_m2",
            "high_risk_area_m2",
            "high_risk_percentage",
            "mean_icra",
            "median_icra",
            "max_icra",
            "std_icra",
            "total_cells",
            "high_risk_cells",
        ]:
            assert field in summary, f"\nsurface_summary.{field} ausente"

        metrics = data["territorial_metrics"]
        for field in [
            "severity_score",
            "criticality_score",
            "dispersion_index",
            "exposure_index",
            "risk_classification",
        ]:
            assert field in metrics, f"\nterritorial_metrics.{field} ausente"

    # =====================================================
    # 02 - INVARIANTES MATEMÁTICAS
    # =====================================================
    def test_02_math_consistency(self):
        _print_header("TEST 06.02 — Invariantes Matemáticas")

        self._ensure_surface_exists()

        response = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics"
        )
        assert response.status_code == 200

        data = response.json()
        summary = data["surface_summary"]
        metrics = data["territorial_metrics"]

        total_area = summary["total_area_m2"]
        high_area = summary["high_risk_area_m2"]
        pct_api = summary["high_risk_percentage"]

        # Área coerente
        assert total_area >= 0
        assert high_area >= 0
        assert high_area <= total_area

        # Percentual coerente
        if total_area > 0:
            pct_calc = high_area / total_area
            assert isclose(pct_calc, pct_api, abs_tol=EPS), (
                f"\nPercentual inconsistente\n"
                f"Calculado: {pct_calc}\n"
                f"API: {pct_api}"
            )

        # Scores entre 0 e 1
        _assert_between(metrics["severity_score"], 0, 1, "severity_score")
        _assert_between(metrics["criticality_score"], 0, 1, "criticality_score")
        _assert_between(metrics["exposure_index"], 0, 1, "exposure_index")
        _assert_between(summary["high_risk_percentage"], 0, 1, "high_risk_percentage")

    # =====================================================
    # 03 - PROPAGAÇÃO DE THRESHOLD
    # =====================================================
    def test_03_threshold_override_behavior(self):
        _print_header("TEST 06.03 — Propagação de Threshold")

        self._ensure_surface_exists()

        r_default = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics"
        )
        exposure_default = r_default.json()["territorial_metrics"]["exposure_index"]

        r_zero = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics?high_risk_threshold=0.0"
        )
        exposure_zero = r_zero.json()["territorial_metrics"]["exposure_index"]

        r_one = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics?high_risk_threshold=1.0"
        )
        exposure_one = r_one.json()["territorial_metrics"]["exposure_index"]

        assert exposure_zero >= exposure_default
        assert exposure_one <= exposure_default

    # =====================================================
    # 04 - ESTRUTURA DA SÉRIE
    # =====================================================
    def test_04_series_structure(self):
        _print_header("TEST 06.04 — Estrutura Série")

        self._ensure_surface_exists()

        response = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics/series"
        )

        assert response.status_code == 200
        data = response.json()

        assert "municipality" in data
        assert "total" in data
        assert "series" in data
        assert "high_risk_threshold" in data

        assert isinstance(data["series"], list)

        if data["series"]:
            item = data["series"][0]
            assert "snapshot_timestamp" in item
            assert "surface_summary" in item
            assert "territorial_metrics" in item

    # =====================================================
    # 05 - ORDEM CRONOLÓGICA
    # =====================================================
    def test_05_series_chronological_order(self):
        _print_header("TEST 06.05 — Ordem Cronológica")

        self._ensure_surface_exists()

        response = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics/series"
        )

        data = response.json()

        timestamps = [
            datetime.fromisoformat(item["snapshot_timestamp"])
            for item in data["series"]
        ]

        assert timestamps == sorted(timestamps), (
            "\nSérie não está em ordem cronológica crescente"
        )

    # =====================================================
    # 06 - FILTRO TEMPORAL
    # =====================================================
    def test_06_series_window_filter(self):
        _print_header("TEST 06.06 — Filtro Temporal")

        self._ensure_surface_exists()

        response = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics/series"
        )

        data = response.json()
        if not data["series"]:
            pytest.skip("Sem dados suficientes para testar filtro temporal")

        first_ts = data["series"][0]["snapshot_timestamp"]

        response_filtered = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics/series?from_ts={first_ts}"
        )

        data_filtered = response_filtered.json()

        for item in data_filtered["series"]:
            assert item["snapshot_timestamp"] >= first_ts

    # =====================================================
    # 07 - COERÊNCIA CLASSIFICAÇÃO
    # =====================================================
    def test_07_classification_coherence(self):
        _print_header("TEST 06.07 — Classificação Coerente")

        self._ensure_surface_exists()

        response = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics"
        )

        data = response.json()

        score = data["territorial_metrics"]["criticality_score"]
        classification = data["territorial_metrics"]["risk_classification"]

        if score <= 0.30:
            assert classification == "Baixo"
        elif score <= 0.50:
            assert classification == "Moderado"
        elif score <= 0.70:
            assert classification == "Alto"
        else:
            assert classification == "Crítico"

    # =====================================================
    # 08 - INTEGRAÇÃO LÓGICA SURFACE vs ANALYTICS
    # =====================================================
    def test_08_surface_vs_analytics_logical_consistency(self):
        _print_header("TEST 06.08 — Integração Lógica Surface vs Analytics")

        self._ensure_surface_exists()

        r_surface = client.get(f"/surface/{self.MUNICIPALITY_ID}")
        r_analytics = client.get(
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics"
        )

        surface = r_surface.json()
        analytics = r_analytics.json()

        surface_high_area = surface["stats"]["high_risk_area_m2"]
        analytics_high_area = analytics["surface_summary"]["high_risk_area_m2"]

        if surface_high_area == 0:
            assert analytics_high_area == 0
