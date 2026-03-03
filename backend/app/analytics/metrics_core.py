"""
analytics/metrics_core.py

Núcleo matemático da camada de Inteligência Territorial (Analytics) do ClimaGyn.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import exp, isfinite, sqrt
from statistics import mean, pstdev
from typing import Dict, List, Optional, Tuple


# ==========================================================
# TIPOS / CONFIG
# ==========================================================

class CompositeMode(str, Enum):
    LINEAR = "linear"
    SIGMOID = "sigmoid"          # dá mais contraste quando se aproxima do crítico
    RISK_AVERSE = "risk_averse"  # penaliza mais concentração/hotspots


@dataclass(frozen=True)
class TerritorialWeights:
    """
    Pesos do índice composto.
    """
    exposure: float = 0.45       # ET
    intensity: float = 0.35      # IMR
    concentration: float = 0.20  # CONC

    def normalized(self) -> "TerritorialWeights":
        s = self.exposure + self.intensity + self.concentration
        if s <= 0:
            return TerritorialWeights(0.45, 0.35, 0.20)
        return TerritorialWeights(
            exposure=self.exposure / s,
            intensity=self.intensity / s,
            concentration=self.concentration / s,
        )


@dataclass(frozen=True)
class TerritorialThresholds:
    """
    Thresholds estratégicos.

    high_risk_threshold deve estar alinhado ao produto (>= 0.7).
    extra thresholds ajudam a identificar hotspots e severidade.
    """
    high_risk_threshold: float = 0.70
    very_high_risk_threshold: float = 0.85
    moderate_risk_threshold: float = 0.50
    stable_max: float = 0.30
    attention_max: float = 0.60
    critical_max: float = 1.00


@dataclass(frozen=True)
class AggregatedSpatialData:
    """
    Agregado territorial mínimo necessário.

    - total_area_m2: área total do município (apenas células dentro do polígono)
    - high_risk_area_m2: soma de áreas de células com ICRA >= high_risk_threshold
    - icra_values: lista de ICRA de todas as células consideradas (dentro do polígono)
    - cell_area_m2: área aproximada de uma célula (ou área média).
    - metadata: livre para anexar infos calculadas em spatial_ops (ex: grid_resolution_m).
    """
    total_area_m2: float
    high_risk_area_m2: float
    icra_values: List[float]
    cell_area_m2: Optional[float] = None
    metadata: Optional[Dict[str, object]] = None


@dataclass(frozen=True)
class TerritorialMetrics:
    """
    Saída final do core.
    """
    exposure_index: float                 
    mean_intensity: float                 
    concentration_index: float            
    hotspot_ratio_high: float            
    hotspot_ratio_very_high: float        
    composite_index: float               
    mode: CompositeMode
    classification: str   # Estável / Atenção / Crítico
    signals: Dict[str, object]


# ==========================================================
# UTILITÁRIOS NUMÉRICOS
# ==========================================================

def _clamp01(x: float) -> float:
    if not isfinite(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _safe_float(x: object, default: float = 0.0) -> float:
    try:
        v = float(x) 
        if not isfinite(v):
            return default
        return v
    except Exception:
        return default


def _sanitize_icra_list(values: List[float]) -> List[float]:
    out: List[float] = []
    for v in values:
        f = _safe_float(v, default=0.0)
        out.append(_clamp01(f))
    return out


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    try:
        return float(mean(values))
    except Exception:
        return 0.0


def _safe_pstdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return float(pstdev(values))
    except Exception:
        return 0.0


def _sigmoid(x: float, k: float = 8.0, x0: float = 0.55) -> float:
    """
    Sigmóide para aumentar contraste.
    k: inclinação
    x0: centro (ponto de inflexão)
    """
    x = _clamp01(x)
    try:
        return float(1.0 / (1.0 + exp(-k * (x - x0))))
    except Exception:
        return x


# ==========================================================
# CALCULADOR PRINCIPAL
# ==========================================================

class TerritorialMetricsCalculator:
    """
    Calculador de métricas territoriais (core matemático).

    Estratégia:
    1) Exposure (ET) = high_risk_area / total_area
    2) Intensity (IMR) = média do ICRA em todas as células
    3) Concentration: usa coeficiente de variação (CV) e hotspot ratios
       - concentração alta = risco "aglomerado" -> operacionalmente mais crítico
       - concentração baixa com intensidade alta = risco difuso (também crítico)
    4) Composto:
       - linear: soma ponderada
       - sigmoid: aplica sigmóide ao linear
       - risk_averse: penaliza hotspots e concentração (não-linear)
    """

    def __init__(
        self,
        weights: Optional[TerritorialWeights] = None,
        thresholds: Optional[TerritorialThresholds] = None,
        composite_mode: CompositeMode = CompositeMode.RISK_AVERSE,
    ) -> None:
        self.weights = (weights or TerritorialWeights()).normalized()
        self.thresholds = thresholds or TerritorialThresholds()
        self.mode = composite_mode

    # ------------------------------------------------------
    # API principal
    # ------------------------------------------------------

    def compute(self, data: AggregatedSpatialData) -> TerritorialMetrics:
        icras = _sanitize_icra_list(data.icra_values)

        total_area = max(_safe_float(data.total_area_m2, 0.0), 0.0)
        high_area = max(_safe_float(data.high_risk_area_m2, 0.0), 0.0)

        exposure = self._compute_exposure_index(total_area, high_area)
        intensity = self._compute_mean_intensity(icras)
        concentration = self._compute_concentration_index(icras)

        hotspot_high, hotspot_vhigh = self._compute_hotspot_ratios(icras)

        composite = self._compute_composite(
            exposure=exposure,
            intensity=intensity,
            concentration=concentration,
            hotspot_high=hotspot_high,
            hotspot_vhigh=hotspot_vhigh,
        )

        classification = self._classify(composite)

        signals = self._build_signals(
            total_area_m2=total_area,
            high_risk_area_m2=high_area,
            exposure=exposure,
            intensity=intensity,
            concentration=concentration,
            hotspot_high=hotspot_high,
            hotspot_vhigh=hotspot_vhigh,
            composite=composite,
            metadata=data.metadata or {},
        )

        return TerritorialMetrics(
            exposure_index=exposure,
            mean_intensity=intensity,
            concentration_index=concentration,
            hotspot_ratio_high=hotspot_high,
            hotspot_ratio_very_high=hotspot_vhigh,
            composite_index=composite,
            mode=self.mode,
            classification=classification,
            signals=signals,
        )

    # ------------------------------------------------------
    # Métricas base
    # ------------------------------------------------------

    def _compute_exposure_index(self, total_area_m2: float, high_risk_area_m2: float) -> float:
        if total_area_m2 <= 0:
            return 0.0
        return _clamp01(high_risk_area_m2 / total_area_m2)

    def _compute_mean_intensity(self, icras: List[float]) -> float:
        return _clamp01(_safe_mean(icras))

    def _compute_concentration_index(self, icras: List[float]) -> float:
        """
        Concentração baseada em:
        - CV = std/mean (quando mean>0)
        - normaliza CV para 0..1 com uma função saturante
        """
        mu = _safe_mean(icras)
        sd = _safe_pstdev(icras)
        if mu <= 1e-9:
            return 0.0

        cv = sd / mu  
        # saturação: cv=0 =>0 ; cv~1 => ~0.63 ; cv~2 => ~0.86
        conc = 1.0 - exp(-cv) if cv > 0 else 0.0
        return _clamp01(conc)

    def _compute_hotspot_ratios(self, icras: List[float]) -> Tuple[float, float]:
        if not icras:
            return 0.0, 0.0
        hi = self.thresholds.high_risk_threshold
        vhi = self.thresholds.very_high_risk_threshold

        n = len(icras)
        r_hi = sum(1 for x in icras if x >= hi) / n
        r_vhi = sum(1 for x in icras if x >= vhi) / n

        return _clamp01(r_hi), _clamp01(r_vhi)

    # ------------------------------------------------------
    # Índice composto (estrategicamente avançado)
    # ------------------------------------------------------

    def _compute_composite(
        self,
        exposure: float,
        intensity: float,
        concentration: float,
        hotspot_high: float,
        hotspot_vhigh: float,
    ) -> float:
        w = self.weights

        linear = (
            w.exposure * exposure +
            w.intensity * intensity +
            w.concentration * concentration
        )
        linear = _clamp01(linear)

        if self.mode == CompositeMode.LINEAR:
            return linear

        if self.mode == CompositeMode.SIGMOID:
            return _clamp01(_sigmoid(linear, k=8.5, x0=0.55))

        a = 0.25
        b = 0.45

        p_hot = a * hotspot_high + b * (hotspot_vhigh ** 0.7)
        p_hot = _clamp01(p_hot)

        diffuse_penalty = 0.0
        if intensity >= 0.60 and concentration <= 0.35:
            # cresce com intensidade e "quanto mais difuso"
            diffuse_penalty = (intensity - 0.60) * (0.35 - concentration) * 1.8
        diffuse_penalty = _clamp01(diffuse_penalty)

        # amplifica exposição + intensidade quando ambos altos (efeito sinérgico)
        synergy = (exposure * intensity) ** 0.65 
        synergy = _clamp01(synergy)

        # base é linear; soma penalidades e sinergia com pesos controlados
        composite = linear
        composite += 0.35 * p_hot
        composite += 0.20 * diffuse_penalty
        composite += 0.15 * synergy

        # normaliza com saturação para manter 0..1 sem “estourar”
        # (saturação tipo 1-exp(-k*x))
        composite = 1.0 - exp(-1.35 * composite)
        return _clamp01(composite)

    # ------------------------------------------------------
    # Classificação
    # ------------------------------------------------------

    def _classify(self, composite_index: float) -> str:
        t = self.thresholds
        x = _clamp01(composite_index)

        if x <= t.stable_max:
            return "Estável"
        if x <= t.attention_max:
            return "Atenção"
        return "Crítico"

    # ------------------------------------------------------
    # Sinais estratégicos 
    # ------------------------------------------------------

    def _build_signals(
        self,
        total_area_m2: float,
        high_risk_area_m2: float,
        exposure: float,
        intensity: float,
        concentration: float,
        hotspot_high: float,
        hotspot_vhigh: float,
        composite: float,
        metadata: Dict[str, object],
    ) -> Dict[str, object]:
        """
        Sinais:
        - recomendação operacional (difuso vs focal)
        - prioridade (baixa/média/alta)
        - “perfil de risco” (hotspot-driven, diffuse-driven, balanced)
        """
        signals: Dict[str, object] = {}

        # área em km² 
        total_km2 = total_area_m2 / 1_000_000 if total_area_m2 > 0 else 0.0
        high_km2 = high_risk_area_m2 / 1_000_000 if high_risk_area_m2 > 0 else 0.0

        signals["area_total_km2"] = round(total_km2, 3)
        signals["area_alto_risco_km2"] = round(high_km2, 3)

        # perfil operacional
        profile = "balanced"
        if hotspot_vhigh >= 0.08 or (hotspot_high >= 0.18 and concentration >= 0.55):
            profile = "hotspot_driven"
        elif intensity >= 0.60 and concentration <= 0.35:
            profile = "diffuse_driven"

        signals["risk_profile"] = profile

        if profile == "hotspot_driven":
            signals["recommended_strategy"] = "Ação focalizada em hotspots (drenagem, limpeza, bloqueios locais, monitoramento intensivo)"
        elif profile == "diffuse_driven":
            signals["recommended_strategy"] = "Ação distribuída (alerta ampliado, logística e equipes móveis, prevenção em múltiplas regiões)"
        else:
            signals["recommended_strategy"] = "Ação mista (hotspots + áreas adjacentes com atenção moderada)"

        # prioridade
        if composite >= 0.75:
            priority = "alta"
        elif composite >= 0.45:
            priority = "média"
        else:
            priority = "baixa"
        signals["priority"] = priority

        # sinais auxiliares para dashboards
        signals["exposure_index"] = round(exposure, 4)
        signals["mean_intensity"] = round(intensity, 4)
        signals["concentration_index"] = round(concentration, 4)
        signals["hotspot_ratio_high"] = round(hotspot_high, 4)
        signals["hotspot_ratio_very_high"] = round(hotspot_vhigh, 4)
        signals["composite_index"] = round(composite, 4)

        if metadata:
            for k in ("grid_resolution_m", "kernel_sigma_m", "snapshot_timestamp", "municipality_id"):
                if k in metadata:
                    signals[k] = metadata[k]

        return signals
