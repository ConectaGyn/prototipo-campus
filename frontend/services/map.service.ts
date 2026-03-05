/**
 * map.service.ts
 *
 * Camada de servico para endpoints de mapa e risco pontual.
 */

import type {
  MapPointsResponse,
  PointRiskSnapshotResponse,
  RiskStatus,
} from "@domains/map/types";
import { API_BASE_URL } from "@services/api.config";

const MAP_POINTS_ENDPOINT = "/map/points";
const POINT_RISK_ENDPOINT = "/points";
const RECOMPUTE_ALL_ENDPOINT = "/points/recompute-all";
const DEFAULT_TIMEOUT_MS = 15000;
const RECOMPUTE_TIMEOUT_MS = 600000;

async function fetchJsonWithTimeout<T>(
  url: string,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  method: "GET" | "POST" = "GET"
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Erro HTTP ${response.status} ao acessar ${url}`);
    }

    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Busca os pontos criticos para renderizacao no mapa.
 * Usa risco no proprio payload (snapshot atual).
 */
export async function getMapPoints(
  municipalityId?: number
): Promise<MapPointsResponse> {
  const cacheBuster = Date.now();
  const params = new URLSearchParams({
    with_risk: "true",
    only_active: "true",
    _ts: String(cacheBuster),
  });
  if (typeof municipalityId === "number") {
    params.set("municipality_id", String(municipalityId));
  }
  const data = await fetchJsonWithTimeout<MapPointsResponse>(
    `${API_BASE_URL}${MAP_POINTS_ENDPOINT}?${params.toString()}`
  );

  if (!data || !Array.isArray(data.pontos)) {
    throw new Error("Resposta invalida do servidor para /map/points.");
  }

  if (typeof data.total !== "number") {
    throw new Error("Resposta invalida do servidor: campo 'total' ausente.");
  }

  if (import.meta.env.DEV) {
    console.debug("[map.service] Pontos do mapa recebidos:", {
      total: data.total,
      snapshot: data.snapshot_timestamp,
    });
  }

  return data;
}

/**
 * Busca o risco associado a um ponto especifico.
 */
export async function getPointRisk(pointId: string): Promise<RiskStatus> {
  if (!pointId) {
    throw new Error("pointId obrigatorio para getPointRisk.");
  }

  const cacheBuster = Date.now();
  const raw = await fetchJsonWithTimeout<PointRiskSnapshotResponse>(
    `${API_BASE_URL}${POINT_RISK_ENDPOINT}/${pointId}/risk?_ts=${cacheBuster}`
  );

  if (!raw || !raw.point_id || !raw.nivel_risco) {
    throw new Error("Resposta invalida do servidor para /points/{id}/risk.");
  }

  return raw;
}

export interface RecomputeAllRiskResponse {
  message: string;
  reference_ts: string;
  points: {
    reference_ts: string;
    total_points: number;
    created: number;
    reused: number;
    failed_count: number;
    failed: Array<{ point_id: string; error: string }>;
  };
  surfaces: {
    ok: number;
    skip_no_points: number;
    failed_count: number;
    failed: Array<{ municipality_id: string; error: string }>;
  };
}

export async function recomputeAllRiskNow(): Promise<RecomputeAllRiskResponse> {
  const cacheBuster = Date.now();
  return fetchJsonWithTimeout<RecomputeAllRiskResponse>(
    `${API_BASE_URL}${RECOMPUTE_ALL_ENDPOINT}?_ts=${cacheBuster}`,
    RECOMPUTE_TIMEOUT_MS,
    "POST"
  );
}
