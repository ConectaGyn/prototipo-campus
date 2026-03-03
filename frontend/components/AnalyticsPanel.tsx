import React, { useCallback, useEffect, useMemo, useState } from 'react';
import type {
  MetricsSeriesItem,
  TerritorialMetricsResponse,
  TerritorialMetricsSeriesResponse,
} from '@domains/analytics/types';
import type { SurfaceEnvelope } from '@domains/surface/types';
import {
  getMunicipalityMetrics,
  getMunicipalityMetricsSeries,
} from '@services/analytics.service';
import { getSurface } from '@services/surface.service';

interface AnalyticsPanelProps {
  municipalityId: number;
}

interface ChartPoint {
  value: number;
}

interface SurfaceDiagnostics {
  absMin: number;
  absMax: number;
  absAvg: number;
  absP75: number;
  absP90: number;
  relMin: number;
  relMax: number;
  relAvg: number;
  relExposure70: number;
}

const DEFAULT_LIMIT = 30;

function toPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function fmtM2(value: number): string {
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(value);
}

function fmtDate(value: string): string {
  return new Date(value).toLocaleString('pt-BR');
}

function clamp01(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function percentile(values: number[], q: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor(q * (sorted.length - 1))));
  return sorted[idx];
}

function MiniLineChart({
  points,
  color,
  title,
}: {
  points: ChartPoint[];
  color: string;
  title: string;
}) {
  const width = 640;
  const height = 180;
  const padding = 24;

  const hasPoints = points.length > 1;

  const pathData = useMemo(() => {
    if (!hasPoints) return '';

    const stepX = (width - padding * 2) / (points.length - 1);

    return points
      .map((point, index) => {
        const x = padding + stepX * index;
        const y = padding + (1 - clamp01(point.value)) * (height - padding * 2);
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
      })
      .join(' ');
  }, [hasPoints, points]);

  const latest = points.length > 0 ? points[points.length - 1].value : 0;

  return (
    <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</h4>
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Atual: {toPct(latest)}</span>
      </div>

      {hasPoints ? (
        <svg viewBox={`0 0 ${width} ${height}`} className="h-36 w-full" role="img" aria-label={title}>
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#94a3b8" strokeOpacity="0.4" />
          <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#94a3b8" strokeOpacity="0.4" />
          <path d={pathData} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
        </svg>
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">Historico insuficiente para grafico.</p>
      )}
    </article>
  );
}

const AnalyticsPanel: React.FC<AnalyticsPanelProps> = ({ municipalityId }) => {
  const [metrics, setMetrics] = useState<TerritorialMetricsResponse | null>(null);
  const [series, setSeries] = useState<TerritorialMetricsSeriesResponse | null>(null);
  const [surface, setSurface] = useState<SurfaceEnvelope | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [limit, setLimit] = useState<number>(DEFAULT_LIMIT);
  const [threshold, setThreshold] = useState<string>('default');

  const numericThreshold = useMemo(() => {
    if (threshold === 'default') return undefined;
    const n = Number(threshold);
    return Number.isFinite(n) ? n : undefined;
  }, [threshold]);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [current, history, currentSurface] = await Promise.all([
        getMunicipalityMetrics(municipalityId, {
          highRiskThreshold: numericThreshold,
        }),
        getMunicipalityMetricsSeries(municipalityId, {
          limit,
          highRiskThreshold: numericThreshold,
        }),
        getSurface(municipalityId),
      ]);

      setMetrics(current);
      setSeries(history);
      setSurface(currentSurface);
    } catch (err: any) {
      console.error('Erro ao carregar analytics:', err);
      setError('Nao foi possivel carregar as analises territoriais.');
      setMetrics(null);
      setSeries(null);
      setSurface(null);
    } finally {
      setLoading(false);
    }
  }, [municipalityId, limit, numericThreshold]);

  useEffect(() => {
    void fetchAnalytics();
  }, [fetchAnalytics]);

  const seriesRows: MetricsSeriesItem[] = series?.series ?? [];

  const criticalityPoints: ChartPoint[] = useMemo(
    () => seriesRows.map((item) => ({ value: item.territorial_metrics.criticality_score })),
    [seriesRows]
  );

  const exposurePoints: ChartPoint[] = useMemo(
    () => seriesRows.map((item) => ({ value: item.territorial_metrics.exposure_index })),
    [seriesRows]
  );

  const trend = useMemo(() => {
    if (seriesRows.length < 2) {
      return {
        criticalityDelta: 0,
        exposureDelta: 0,
      };
    }

    const first = seriesRows[0];
    const last = seriesRows[seriesRows.length - 1];

    return {
      criticalityDelta:
        last.territorial_metrics.criticality_score -
        first.territorial_metrics.criticality_score,
      exposureDelta:
        last.territorial_metrics.exposure_index -
        first.territorial_metrics.exposure_index,
    };
  }, [seriesRows]);

  const diagnostics = useMemo<SurfaceDiagnostics | null>(() => {
    if (!surface || !surface.geojson?.features?.length) return null;

    const absValues = surface.geojson.features
      .map((f: any) => Number(f?.properties?.risk_value))
      .filter((v: number) => Number.isFinite(v));

    const relValues = surface.geojson.features
      .map((f: any) => Number(f?.properties?.risk_value_relative))
      .filter((v: number) => Number.isFinite(v));

    if (absValues.length === 0) return null;

    const relExposure70 = relValues.length
      ? relValues.filter((v) => v >= 0.7).length / relValues.length
      : 0;

    return {
      absMin: Math.min(...absValues),
      absMax: Math.max(...absValues),
      absAvg: absValues.reduce((acc, v) => acc + v, 0) / absValues.length,
      absP75: percentile(absValues, 0.75),
      absP90: percentile(absValues, 0.9),
      relMin: relValues.length ? Math.min(...relValues) : 0,
      relMax: relValues.length ? Math.max(...relValues) : 0,
      relAvg: relValues.length
        ? relValues.reduce((acc, v) => acc + v, 0) / relValues.length
        : 0,
      relExposure70,
    };
  }, [surface]);

  const effectiveThreshold = metrics?.high_risk_threshold ?? 0.7;

  const relativeAreaM2 = useMemo(() => {
    if (!metrics || !diagnostics) return 0;
    return metrics.surface_summary.total_area_m2 * diagnostics.relExposure70;
  }, [metrics, diagnostics]);

  const priority = useMemo(() => {
    if (!metrics) return 'Media';

    const c = metrics.territorial_metrics.criticality_score;
    const eAbs = metrics.territorial_metrics.exposure_index;
    const eRel = diagnostics?.relExposure70 ?? 0;

    if (c >= 0.7 || eAbs >= 0.35 || eRel >= 0.35) return 'Alta';
    if (c >= 0.45 || eAbs >= 0.2 || eRel >= 0.2) return 'Media';
    return 'Baixa';
  }, [metrics, diagnostics]);

  const mismatchFlag = useMemo(() => {
    if (!metrics || !diagnostics) return false;
    return metrics.territorial_metrics.exposure_index <= 0.02 && diagnostics.relExposure70 >= 0.2;
  }, [metrics, diagnostics]);

  const insights = useMemo(() => {
    if (!metrics) return [] as string[];

    const out: string[] = [];
    const c = metrics.territorial_metrics.criticality_score;
    const eAbs = metrics.territorial_metrics.exposure_index;
    const s = metrics.territorial_metrics.severity_score;
    const d = metrics.territorial_metrics.dispersion_index;
    const eRel = diagnostics?.relExposure70 ?? 0;

    if (mismatchFlag) {
      out.push('Mapa relativo indica concentracao territorial relevante, mas a exposicao absoluta esta baixa no threshold atual. Avaliar calibracao do threshold.');
    }

    if (c >= 0.7) {
      out.push('Acionar plano de resposta ampliado com equipes de campo em regime de prioridade alta.');
    } else if (c >= 0.5) {
      out.push('Manter operacao preventiva reforcada e monitoramento por turno da criticidade territorial.');
    } else {
      out.push('Manter monitoramento ativo com foco em prevencao e prontidao operacional.');
    }

    if (Math.max(eAbs, eRel) >= 0.3) {
      out.push('Expandir comunicacao de risco e preparar recursos de resposta para maior cobertura territorial.');
    } else {
      out.push('Concentrar recursos em setores prioritarios para elevar eficiencia da resposta.');
    }

    if (d >= 0.12 && s >= 0.55) {
      out.push('Risco heterogeneo e intenso: combinar resposta focal em hotspots com vigilancia em areas adjacentes.');
    } else if (d < 0.08 && s >= 0.55) {
      out.push('Risco difuso: priorizar acoes distribuidas de logistica e comunicacao territorial.');
    } else {
      out.push('Padrao de risco relativamente estavel: acompanhar tendencia antes de escalonar recursos extras.');
    }

    return out;
  }, [metrics, diagnostics, mismatchFlag]);

  const classificationStyles = (classification?: string) => {
    if (classification === 'Critico') {
      return 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700';
    }
    if (classification === 'Alto') {
      return 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700';
    }
    if (classification === 'Moderado') {
      return 'bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700';
    }
    return 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700';
  };

  return (
    <section className="max-w-screen-2xl mx-auto px-3 pb-6 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-700 dark:text-slate-200">Analises Territoriais</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Painel para apoio a decisao de gestores publicos com foco em priorizacao de resposta.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs text-slate-500 dark:text-slate-400">
            Threshold absoluto
            <select
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="ml-2 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:bg-slate-800 dark:border-slate-600"
            >
              <option value="default">Padrao</option>
              <option value="0.10">0.10</option>
              <option value="0.20">0.20</option>
              <option value="0.40">0.40</option>
              <option value="0.70">0.70</option>
            </select>
          </label>

          <label className="text-xs text-slate-500 dark:text-slate-400">
            Janela
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="ml-2 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:bg-slate-800 dark:border-slate-600"
            >
              <option value={12}>12 snapshots</option>
              <option value={24}>24 snapshots</option>
              <option value={30}>30 snapshots</option>
              <option value={60}>60 snapshots</option>
            </select>
          </label>

          <button
            type="button"
            onClick={() => void fetchAnalytics()}
            className="rounded-md border border-cyan-600 px-3 py-1 text-sm font-medium text-cyan-700 hover:bg-cyan-50 dark:text-cyan-300 dark:border-cyan-500 dark:hover:bg-slate-800"
          >
            Atualizar
          </button>
        </div>
      </div>

      {loading && (
        <div className="rounded-lg border border-slate-200 bg-white/70 p-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-300">
          Carregando analises...
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-700 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && metrics && (
        <>
          <div className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Prioridade operacional</p>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{priority}</p>
              </div>

              <div className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${classificationStyles(metrics.territorial_metrics.risk_classification)}`}>
                Classificacao atual: {metrics.territorial_metrics.risk_classification}
              </div>

              <div className="text-xs text-slate-500 dark:text-slate-400">
                Janela analisada: {series?.total ?? 0} snapshots
              </div>
            </div>
          </div>

          {mismatchFlag && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">
              Divergencia detectada: exposicao absoluta muito baixa com concentracao relativa elevada no mapa. Recomendado revisar threshold absoluto para leitura executiva.
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <p className="text-xs text-slate-500 dark:text-slate-400">Criticidade</p>
              <p className="mt-2 text-2xl font-bold text-slate-800 dark:text-slate-100">
                {toPct(metrics.territorial_metrics.criticality_score)}
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Tendencia: {trend.criticalityDelta >= 0 ? '+' : '-'}{toPct(Math.abs(trend.criticalityDelta))}
              </p>
            </article>

            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <p className="text-xs text-slate-500 dark:text-slate-400">Exposicao absoluta (institucional)</p>
              <p className="mt-2 text-2xl font-bold text-slate-800 dark:text-slate-100">
                {toPct(metrics.territorial_metrics.exposure_index)}
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Threshold: {effectiveThreshold.toFixed(2)}</p>
            </article>

            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <p className="text-xs text-slate-500 dark:text-slate-400">Exposicao relativa (mapa)</p>
              <p className="mt-2 text-2xl font-bold text-slate-800 dark:text-slate-100">
                {toPct(diagnostics?.relExposure70 ?? 0)}
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Referencia: risco relativo {'>='} 0.70</p>
            </article>

            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <p className="text-xs text-slate-500 dark:text-slate-400">Severidade media</p>
              <p className="mt-2 text-2xl font-bold text-slate-800 dark:text-slate-100">
                {toPct(metrics.territorial_metrics.severity_score)}
              </p>
            </article>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            <MiniLineChart
              points={criticalityPoints}
              color="#dc2626"
              title="Tendencia de criticidade (janela selecionada)"
            />
            <MiniLineChart
              points={exposurePoints}
              color="#0ea5e9"
              title="Tendencia de exposicao absoluta"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <p className="text-xs text-slate-500 dark:text-slate-400">Area total analisada</p>
              <p className="mt-2 text-xl font-semibold text-slate-800 dark:text-slate-100">
                {fmtM2(metrics.surface_summary.total_area_m2)} m2
              </p>
            </article>

            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <p className="text-xs text-slate-500 dark:text-slate-400">Area alto risco absoluta</p>
              <p className="mt-2 text-xl font-semibold text-slate-800 dark:text-slate-100">
                {fmtM2(metrics.surface_summary.high_risk_area_m2)} m2
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {toPct(metrics.surface_summary.high_risk_percentage)} da area total
              </p>
            </article>

            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <p className="text-xs text-slate-500 dark:text-slate-400">Area alta relativa (estimada)</p>
              <p className="mt-2 text-xl font-semibold text-slate-800 dark:text-slate-100">
                {fmtM2(relativeAreaM2)} m2
              </p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Baseado em risco relativo {'>='} 0.70
                </p>
            </article>
          </div>

          {diagnostics && (
            <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">Calibracao de escala absoluta</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900/50">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Faixa absoluta observada</p>
                  <p className="mt-1 font-semibold text-slate-700 dark:text-slate-200">
                    min {diagnostics.absMin.toFixed(4)} | max {diagnostics.absMax.toFixed(4)}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">media {diagnostics.absAvg.toFixed(4)}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900/50">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Percentis de referencia</p>
                  <p className="mt-1 font-semibold text-slate-700 dark:text-slate-200">
                    p75 {diagnostics.absP75.toFixed(4)} | p90 {diagnostics.absP90.toFixed(4)}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900/50">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Ajuste rapido de threshold</p>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800"
                      onClick={() => setThreshold(diagnostics.absP75.toFixed(2))}
                    >
                      Usar p75
                    </button>
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800"
                      onClick={() => setThreshold(diagnostics.absP90.toFixed(2))}
                    >
                      Usar p90
                    </button>
                  </div>
                </div>
              </div>
            </article>
          )}

          <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">Insights para decisao</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {insights.map((text, index) => (
                <div key={`insight-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300">
                  {text}
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-800/70">
            <div className="flex items-center justify-between gap-2 mb-3">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Historico detalhado</h3>
              <span className="text-xs text-slate-500 dark:text-slate-400">{series?.total ?? 0} snapshots</span>
            </div>

            {seriesRows.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Sem historico suficiente no periodo selecionado.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                      <th className="py-2 pr-4">Snapshot</th>
                      <th className="py-2 pr-4">Classificacao</th>
                      <th className="py-2 pr-4">Criticidade</th>
                      <th className="py-2 pr-4">Exposicao abs.</th>
                      <th className="py-2 pr-4">Severidade</th>
                      <th className="py-2">Area alto risco</th>
                    </tr>
                  </thead>
                  <tbody>
                    {seriesRows.map((item) => (
                      <tr key={item.snapshot_timestamp} className="border-b border-slate-100 dark:border-slate-800 text-slate-700 dark:text-slate-200">
                        <td className="py-2 pr-4 whitespace-nowrap">{fmtDate(item.snapshot_timestamp)}</td>
                        <td className="py-2 pr-4">{item.territorial_metrics.risk_classification}</td>
                        <td className="py-2 pr-4">{toPct(item.territorial_metrics.criticality_score)}</td>
                        <td className="py-2 pr-4">{toPct(item.territorial_metrics.exposure_index)}</td>
                        <td className="py-2 pr-4">{toPct(item.territorial_metrics.severity_score)}</td>
                        <td className="py-2">{fmtM2(item.surface_summary.high_risk_area_m2)} m2</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>

          <div className="text-xs text-slate-500 dark:text-slate-400">
            <p>
              Referencia: {fmtDate(metrics.surface.snapshot_timestamp)} | Validade: {metrics.surface.valid_until ? fmtDate(metrics.surface.valid_until) : 'n/a'}
            </p>
            <p>
              Leitura institucional usa escala absoluta (threshold configuravel). Mapa visual usa escala relativa.
            </p>
          </div>
        </>
      )}
    </section>
  );
};

export default AnalyticsPanel;
