import pytest
from datetime import datetime
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple

from backend.app.tests.utils.http_client import client


MUNICIPALITY_ID_DEFAULT = 1

BASELINE_RUNS = 8
STABILITY_RUNS = 25

LIMITS_MS = {
    "surface": {"ok": 2400.0, "critical": 5000.0},
    "metrics": {"ok": 3000.0, "critical": 6000.0},
    "series": {"ok": 5000.0, "critical": 20000.0},
}

DRIFT_WARN_FACTOR = 1.50
DRIFT_FAIL_FACTOR = 2.10

P95_Q = 0.95

# =====================================================
# Helpers de logging
# =====================================================

def _print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def _print_kv(label: str, value: Any) -> None:
    print(f"{label}: {value}")


def _status_tag(ok: bool, warn: bool = False) -> str:
    if ok and not warn:
        return "PASS ✅"
    if ok and warn:
        return "WARN ⚠️"
    return "FAIL ❌"


# =====================================================
# Helpers estatísticos
# =====================================================

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stddev_pop(xs: List[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mu = _mean(xs)
    var = sum((x - mu) ** 2 for x in xs) / n
    return sqrt(var)


def _pctl(xs: List[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    idx = int(round((len(s) - 1) * q))
    idx = max(0, min(idx, len(s) - 1))
    return float(s[idx])


def _summary_stats(samples_ms: List[float]) -> Dict[str, float]:
    if not samples_ms:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "p95": 0.0}
    return {
        "min": float(min(samples_ms)),
        "max": float(max(samples_ms)),
        "mean": float(_mean(samples_ms)),
        "std": float(_stddev_pop(samples_ms)),
        "p95": float(_pctl(samples_ms, P95_Q)),
    }


def _drift_assessment(samples_ms: List[float]) -> Tuple[float, str]:
    """
    Retorna:
    - growth_factor (últimos 5 / primeiros 5)
    - status ("ok", "warn", "fail")
    """
    if len(samples_ms) < 10:
        return 1.0, "ok"

    first = samples_ms[:5]
    last = samples_ms[-5:]

    m1 = _mean(first)
    m2 = _mean(last)

    if m1 <= 1e-9:
        return 1.0, "ok"

    factor = m2 / m1

    if factor >= DRIFT_FAIL_FACTOR:
        return factor, "fail"
    if factor >= DRIFT_WARN_FACTOR:
        return factor, "warn"
    return factor, "ok"


# =====================================================
# Helpers HTTP 
# =====================================================

def _resp_body_text(resp) -> str:
    try:
        return resp.raw.text
    except Exception:
        try:
            return str(resp.json())
        except Exception:
            return "<no-body>"


def _get_and_measure(path: str) -> Tuple[int, float, Dict[str, Any]]:
    """
    Faz GET e retorna:
    - status_code
    - elapsed_ms (já vem em APIResponse)
    - json (se possível) ou {}
    """
    resp = client.get(path)
    status = getattr(resp, "status_code", None)
    elapsed_ms = float(getattr(resp, "elapsed_ms", 0.0) or 0.0)

    payload: Dict[str, Any] = {}
    try:
        payload = resp.json()
    except Exception:
        payload = {}

    return int(status), elapsed_ms, payload


def _ensure_surface_exists(municipality_id: int) -> None:
    """
    Garante que o endpoint /surface/{id} está OK antes de testar analytics.
    Isso evita falhas cascata por ausência de superfície/snapshot.
    """
    _print_kv("[HTTP] Warmup GET", f"/surface/{municipality_id}")
    status, ms, _ = _get_and_measure(f"/surface/{municipality_id}")
    print(f"[HTTP] Status: {status} | {ms:.1f} ms")

    assert status == 200, (
        f"\nWarmup /surface falhou.\n"
        f"Status: {status}\n"
        f"Path: /surface/{municipality_id}\n"
    )


def _run_latency_baseline(
    *,
    label: str,
    path: str,
    runs: int,
    ok_limit_ms: float,
    critical_limit_ms: float,
) -> Dict[str, Any]:
    """
    Executa N chamadas e avalia limites.
    Retorna dict com estatísticas e flags.
    """
    samples: List[float] = []
    statuses: List[int] = []

    print(f"[TARGET] {path}")
    for i in range(1, runs + 1):
        status, ms, _ = _get_and_measure(path)
        statuses.append(status)
        samples.append(ms)
        print(f"[RUN {i:02d}] {ms:.1f} ms | status={status}")

    stats = _summary_stats(samples)

    all_200 = all(s == 200 for s in statuses)

    warn = False
    ok = True

    if not all_200:
        ok = False

    if stats["mean"] > critical_limit_ms:
        ok = False
    elif stats["mean"] > ok_limit_ms:
        warn = True

    drift_factor, drift_status = _drift_assessment(samples)

    if drift_status == "fail":
        ok = False
    elif drift_status == "warn":
        warn = True

    tag = _status_tag(ok, warn)

    print("\n[SUMMARY]")
    _print_kv("Min (ms)", f"{stats['min']:.1f}")
    _print_kv("Max (ms)", f"{stats['max']:.1f}")
    _print_kv("Mean (ms)", f"{stats['mean']:.1f}")
    _print_kv("StdDev (ms)", f"{stats['std']:.1f}")
    _print_kv("P95 (ms)", f"{stats['p95']:.1f}")
    _print_kv("Drift Factor", f"{drift_factor:.2f}")
    _print_kv("Status", tag)

    return {
        "ok": ok,
        "warn": warn,
        "stats": stats,
        "drift_factor": drift_factor,
    }


# =====================================================
# TEST CLASS
# =====================================================

class TestPerformanceSmoke:

    MUNICIPALITY_ID = MUNICIPALITY_ID_DEFAULT

    # -------------------------------------------------
    # 07.01 — Surface Baseline
    # -------------------------------------------------

    def test_01_surface_latency_baseline(self):
        _print_header("TEST 07.01 — Surface Baseline Latency")

        result = _run_latency_baseline(
            label="surface",
            path=f"/surface/{self.MUNICIPALITY_ID}",
            runs=BASELINE_RUNS,
            ok_limit_ms=LIMITS_MS["surface"]["ok"],
            critical_limit_ms=LIMITS_MS["surface"]["critical"],
        )

        assert result["ok"], "Surface baseline excedeu limite crítico."

    # -------------------------------------------------
    # 07.02 — Analytics Metrics Baseline
    # -------------------------------------------------

    def test_02_metrics_latency_baseline(self):
        _print_header("TEST 07.02 — Metrics Baseline Latency")

        _ensure_surface_exists(self.MUNICIPALITY_ID)

        result = _run_latency_baseline(
            label="metrics",
            path=f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics",
            runs=BASELINE_RUNS,
            ok_limit_ms=LIMITS_MS["metrics"]["ok"],
            critical_limit_ms=LIMITS_MS["metrics"]["critical"],
        )

        assert result["ok"], "Metrics baseline excedeu limite crítico."

    # -------------------------------------------------
    # 07.03 — Series Baseline
    # -------------------------------------------------

    def test_03_series_latency_baseline(self):
        _print_header("TEST 07.03 — Series Baseline Latency")

        _ensure_surface_exists(self.MUNICIPALITY_ID)

        result = _run_latency_baseline(
            label="series",
            path=f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics/series",
            runs=BASELINE_RUNS,
            ok_limit_ms=LIMITS_MS["series"]["ok"],
            critical_limit_ms=LIMITS_MS["series"]["critical"],
        )

        assert result["ok"], "Series baseline excedeu limite crítico."

    # -------------------------------------------------
    # 07.04 — Stability Test (Repetição)
    # -------------------------------------------------

    def test_04_repeated_calls_stability(self):
        _print_header("TEST 07.04 — Repeated Calls Stability")

        _ensure_surface_exists(self.MUNICIPALITY_ID)

        samples: List[float] = []
        statuses: List[int] = []

        path = f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics"

        print(f"[TARGET] {path}")

        for i in range(1, STABILITY_RUNS + 1):
            status, ms, _ = _get_and_measure(path)
            statuses.append(status)
            samples.append(ms)
            print(f"[RUN {i:02d}] {ms:.1f} ms | status={status}")

        assert all(s == 200 for s in statuses), "Erro intermitente detectado (status != 200)."

        drift_factor, drift_status = _drift_assessment(samples)

        print("\n[DRIFT ANALYSIS]")
        _print_kv("Drift Factor", f"{drift_factor:.2f}")
        _print_kv("Drift Status", drift_status)

        assert drift_status != "fail", "Degradação progressiva severa detectada."

    # -------------------------------------------------
    # 07.05 — Encadeado (State Consistency)
    # -------------------------------------------------

    def test_05_chain_calls_consistency(self):
        _print_header("TEST 07.05 — Chain Calls Consistency")

        paths = [
            f"/surface/{self.MUNICIPALITY_ID}",
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics",
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics/series",
            f"/surface/{self.MUNICIPALITY_ID}",
            f"/analytics/municipalities/{self.MUNICIPALITY_ID}/metrics",
        ]

        for idx, path in enumerate(paths, start=1):
            status, ms, _ = _get_and_measure(path)
            print(f"[CHAIN {idx}] {path} | {ms:.1f} ms | status={status}")
            assert status == 200, f"Falha em chamada encadeada: {path}"

        print("\n[RESULT]")
        print("Encadeamento executado com sucesso sem inconsistência.")
