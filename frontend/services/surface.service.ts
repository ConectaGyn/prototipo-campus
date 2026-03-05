/**
 * surface.service.ts
 *
 * Camada de serviço responsável por comunicação com os endpoints
 * relacionados à superfície espacial (heatmap territorial).
 *
 * Responsabilidades:
 * - Buscar superfície completa (GeoJSON + estatísticas)
 * - Buscar apenas metadados
 * - Garantir timeout e abort
 * - Validar estrutura mínima da resposta
 *
 * NÃO contém:
 * - Lógica de UI
 * - Lógica de mapa (Leaflet)
 * - Transformações geométricas
 * - Cálculos espaciais
 */

import type {
  SurfaceEnvelope,
} from "@domains/surface/types";
import { API_BASE_URL } from "@services/api.config";

const SURFACE_ENDPOINT = "/surface";

const DEFAULT_TIMEOUT_MS = 15000;

/**
 * Helper interno para fetch com AbortController e timeout.
 */
async function fetchWithTimeout<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      cache: "no-store",
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(
        `Erro HTTP ${response.status} ao acessar ${url}`
      );
    }

    const data = await response.json();
    return data as T;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getSurface(
  municipalityId: number
): Promise<SurfaceEnvelope> {
  if (municipalityId === undefined || municipalityId === null) {
    throw new Error("municipalityId inválido para getSurface().");
  }

  const url = `${API_BASE_URL}${SURFACE_ENDPOINT}/${municipalityId}`;
  const cacheBusterUrl = `${url}${url.includes("?") ? "&" : "?"}_ts=${Date.now()}`;

  const data = await fetchWithTimeout<SurfaceEnvelope>(cacheBusterUrl, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  // ===============================
  // Validação defensiva
  // ===============================

  if (!data) {
    throw new Error("Resposta vazia ao buscar superfície.");
  }

  if (!data.geojson || data.geojson.type !== "FeatureCollection") {
    throw new Error(
      "Resposta inválida: 'geojson' ausente ou não é FeatureCollection."
    );
  }

  if (!data.reference_ts) {
    throw new Error(
      "Resposta inválida: 'reference_ts' ausente."
    );
  }

  if (!data.stats) {
    throw new Error(
      "Resposta inválida: 'stats' ausente."
    );
  }

  if (import.meta.env.DEV) {
    console.debug("[surface.service] Superfície carregada:", {
      municipalityId,
      reference: data.reference_ts,
      totalCells: data.stats.total_cells,
      highRiskPercentage: data.stats.high_risk_percentage,
    });
  }

  return data;
}

export async function getSurfaceMetadata(
  municipalityId: number
): Promise<Omit<SurfaceEnvelope, "geojson">> {
  if (municipalityId === undefined || municipalityId === null) {
    throw new Error("municipalityId inválido para getSurfaceMetadata().");
  }

  const url = `${API_BASE_URL}${SURFACE_ENDPOINT}/${municipalityId}/metadata`;
  const cacheBusterUrl = `${url}${url.includes("?") ? "&" : "?"}_ts=${Date.now()}`;

  const data = await fetchWithTimeout<Omit<SurfaceEnvelope, "geojson">>(cacheBusterUrl, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!data) {
    throw new Error("Resposta vazia ao buscar metadata da superfície.");
  }

  if (!data.reference_ts) {
    throw new Error(
      "Resposta inválida: 'reference_ts' ausente."
    );
  }

  if (!data.stats) {
    throw new Error(
      "Resposta inválida: 'stats' ausente."
    );
  }

  if (import.meta.env.DEV) {
    console.debug("[surface.service] Metadata carregada:", {
      municipalityId,
      reference: data.reference_ts,
      totalCells: data.stats.total_cells,
    });
  }

  return data;
}
