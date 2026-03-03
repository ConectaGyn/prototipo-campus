const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function normalizeBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;

export const API_BASE_URL = normalizeBaseUrl(rawBaseUrl);
