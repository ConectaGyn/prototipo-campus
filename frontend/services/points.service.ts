import { API_BASE_URL } from "@services/api.config";

const POINTS_ENDPOINT = "/points";
const DEFAULT_TIMEOUT_MS = 15000;

export interface PointItem {
  id: string;
  name: string;
  municipality_id: number | null;
  latitude: number;
  longitude: number;
  active: boolean;
  influence_radius_m: number;
  neighborhood: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

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

export async function getPoints(): Promise<PointItem[]> {
  const url = `${API_BASE_URL}${POINTS_ENDPOINT}`;
  const data = await fetchJsonWithTimeout<PointItem[]>(url);

  if (!Array.isArray(data)) {
    throw new Error("Resposta invalida ao buscar pontos.");
  }

  return data;
}
