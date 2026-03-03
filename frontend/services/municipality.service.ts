import { API_BASE_URL } from "@services/api.config";

const MUNICIPALITIES_ENDPOINT = "/municipalities";
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

export async function getMunicipalityGeoJson(
  municipalityId: number
): Promise<Record<string, unknown>> {
  if (municipalityId === undefined || municipalityId === null) {
    throw new Error("municipalityId invalido para getMunicipalityGeoJson.");
  }

  const url = `${API_BASE_URL}${MUNICIPALITIES_ENDPOINT}/${municipalityId}/geojson`;
  const data = await fetchJsonWithTimeout<Record<string, unknown>>(url);

  if (!data || typeof data !== "object") {
    throw new Error("Resposta invalida ao buscar GeoJSON do municipio.");
  }

  return data;
}
