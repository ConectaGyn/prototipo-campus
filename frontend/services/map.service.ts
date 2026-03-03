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
const DEFAULT_TIMEOUT_MS = 15000;

async function fetchJsonWithTimeout<T>(url: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
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
export async function getMapPoints(): Promise<MapPointsResponse> {
  const data = await fetchJsonWithTimeout<MapPointsResponse>(
    `${API_BASE_URL}${MAP_POINTS_ENDPOINT}?with_risk=true`
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

  const raw = await fetchJsonWithTimeout<PointRiskSnapshotResponse>(
    `${API_BASE_URL}${POINT_RISK_ENDPOINT}/${pointId}/risk`
  );

  if (!raw || !raw.point_id || !raw.nivel_risco) {
    throw new Error("Resposta invalida do servidor para /points/{id}/risk.");
  }

  return raw;
}
