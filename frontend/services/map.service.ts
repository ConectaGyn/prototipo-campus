/**
 * map.service.ts
 *
 * Camada de serviço responsável por buscar os pontos críticos
 * com informações de risco no backend.
 *
 * Este módulo:
 * - NÃO contém lógica de UI
 * - NÃO conhece componentes React
 * - APENAS comunica com a API
 */

import type { MapPointsResponse } from "@domains/map/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
const MAP_POINTS_ENDPOINT = "/map/points";

/**
 * Busca os pontos críticos para renderização no mapa.
 *
 * @returns Lista de pontos críticos com risco (ou risco nulo)
 */
export async function getMapPoints(): Promise<MapPointsResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000); // 15 segundos

  let response: Response;

  try {
    response = await fetch(`${BASE_URL}${MAP_POINTS_ENDPOINT}`, {
      method: 'GET',
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(
        `Erro ao buscar pontos do mapa: ${response.status} ${response.statusText}`
      );
    }

  const data: MapPointsResponse = await response.json();

  if (!data.pontos || !Array.isArray(data.pontos)) {
    throw new Error("Resposta inválida do servidor: 'pontos' ausente ou inválido.");
  }

  if (import.meta.env.DEV) {
    console.debug("[map.service] Pontos do mapa recebidos:", data.pontos);
  }

  return data;
} finally {
    clearTimeout(timeout);
 }

}
