// frontend/services/analytics.service.ts
//
// Camada de serviço para Analytics (Inteligência Territorial).
//
// Responsabilidades:
// - Somente comunicação com API (fetch)
// - Timeout + AbortController
// - Validação mínima do payload (contrato básico)
// - Suporte a filtros (threshold, janela temporal, limit)
//
// NÃO faz:
// - cálculo, agregação, charts
// - lógica de UI/React
//

import type {
  TerritorialMetricsResponse,
  TerritorialMetricsSeriesResponse,
} from "@domains/analytics/types";
import { API_BASE_URL } from "@services/api.config";

const ANALYTICS_BASE = "/analytics/municipalities";
const DEFAULT_TIMEOUT_MS = 15000;

type FetchJsonOptions = {
  timeoutMs?: number;
  signal?: AbortSignal;
};

function buildQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined) continue;
    q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

async function fetchJson<T>(url: string, opts: FetchJsonOptions = {}): Promise<T> {
  const controller = new AbortController();
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  if (opts.signal) {
    if (opts.signal.aborted) controller.abort();
    else opts.signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      let bodyText = "";
      try {
        bodyText = await response.text();
      } catch {
        bodyText = "";
      }
      throw new Error(`HTTP ${response.status} ${response.statusText}${bodyText ? ` | ${bodyText}` : ""}`);
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err?.name === "AbortError") {
      throw new Error(`Timeout/Abort ao chamar API: ${url}`);
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

function assertMetricsResponseShape(data: any): asserts data is TerritorialMetricsResponse {
  if (!data || typeof data !== "object") throw new Error("Resposta inválida: payload vazio.");
  if (!data.municipality) throw new Error("Resposta inválida: municipality ausente.");
  if (!data.surface) throw new Error("Resposta inválida: surface ausente.");
  if (!data.surface_summary) throw new Error("Resposta inválida: surface_summary ausente.");
  if (!data.territorial_metrics) throw new Error("Resposta inválida: territorial_metrics ausente.");
}

function assertMetricsSeriesResponseShape(data: any): asserts data is TerritorialMetricsSeriesResponse {
  if (!data || typeof data !== "object") throw new Error("Resposta inválida: payload vazio.");
  if (!data.municipality) throw new Error("Resposta inválida: municipality ausente.");
  if (!Array.isArray(data.series)) throw new Error("Resposta inválida: series ausente ou não é array.");
  if (typeof data.total !== "number") throw new Error("Resposta inválida: total ausente/inválido.");
}

/**
 * GET /analytics/municipalities/{municipality_id}/metrics
 *
 * @param municipalityId - id do município (ex: 1)
 * @param highRiskThreshold - opcional (0..1). Será enviado em 2 chaves para compatibilidade:
 */
export async function getMunicipalityMetrics(
  municipalityId: number,
  options?: {
    highRiskThreshold?: number;
    timeoutMs?: number;
    signal?: AbortSignal;
  }
): Promise<TerritorialMetricsResponse> {
  const { highRiskThreshold, timeoutMs, signal } = options || {};

  const query = buildQuery({
    high_risk_threshold: highRiskThreshold,
    threshold_high: highRiskThreshold,
  });

  const url = `${API_BASE_URL}${ANALYTICS_BASE}/${municipalityId}/metrics${query}`;

  const data = await fetchJson<TerritorialMetricsResponse>(url, { timeoutMs, signal });

  if (import.meta.env.DEV) {
    console.debug("[analytics.service] metrics recebido:", data);
  }

  assertMetricsResponseShape(data);
  return data;
}

/**
 * GET /analytics/municipalities/{municipality_id}/metrics/series
 *
 * @param municipalityId - id do município
 * @param limit - default 30
 * @param fromTs - ISO string (ex: 2026-02-21T00:00:00-03:00)
 * @param toTs - ISO string
 * @param highRiskThreshold - opcional (0..1) 
 */
export async function getMunicipalityMetricsSeries(
  municipalityId: number,
  options?: {
    limit?: number;
    fromTs?: string;
    toTs?: string;
    highRiskThreshold?: number;
    timeoutMs?: number;
    signal?: AbortSignal;
  }
): Promise<TerritorialMetricsSeriesResponse> {
  const { limit, fromTs, toTs, highRiskThreshold, timeoutMs, signal } = options || {};

  const query = buildQuery({
    limit: limit ?? 30,
    from_ts: fromTs,
    to_ts: toTs,

    high_risk_threshold: highRiskThreshold,
    threshold_high: highRiskThreshold,
  });

  const url = `${API_BASE_URL}${ANALYTICS_BASE}/${municipalityId}/metrics/series${query}`;

  const data = await fetchJson<TerritorialMetricsSeriesResponse>(url, { timeoutMs, signal });

  if (import.meta.env.DEV) {
    console.debug("[analytics.service] series recebido:", data);
  }

  assertMetricsSeriesResponseShape(data);
  return data;
}
