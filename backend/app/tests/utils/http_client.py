"""
utils/http_client.py

Cliente HTTP institucional para testes E2E reais do ClimaGyn.

Objetivos:
- Bater na API real rodando via Uvicorn
- Logar requisição/resposta de forma clara
- Medir tempo de resposta
- Fornecer assert elegante de status code
- Evitar duplicação de código nos testes
"""

from __future__ import annotations

import requests
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


# ============================================================
# CONFIG
# ============================================================

DEFAULT_TIMEOUT_SECONDS = 30


def _resolve_base_url() -> str:
    """
    Permite sobrescrever via variável de ambiente:
        API_BASE_URL=http://127.0.0.1:8000
    """
    return os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


# ============================================================
# RESPONSE WRAPPER
# ============================================================

@dataclass
class APIResponse:
    """
    Wrapper institucional da resposta HTTP.
    """
    status_code: int
    elapsed_ms: float
    raw: requests.Response

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        try:
            return self.raw.json()
        except Exception:
            raise AssertionError(
                f"Resposta não é JSON válido.\n"
                f"Status: {self.status_code}\n"
                f"Body: {self.raw.text[:500]}"
            )

    def assert_status(self, expected_status: int) -> None:
        if self.status_code != expected_status:
            raise AssertionError(
                f"\n[HTTP ASSERT ERROR]\n"
                f"Esperado: {expected_status}\n"
                f"Recebido: {self.status_code}\n"
                f"Body: {self.raw.text[:500]}"
            )


# ============================================================
# API CLIENT
# ============================================================

class APIClient:
    """
    Cliente HTTP para testes reais.

    Uso:
        api = APIClient()
        resp = api.get("/health")
        resp.assert_status(200)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        verbose: bool = True,
    ) -> None:
        self.base_url = (base_url or _resolve_base_url()).rstrip("/")
        self.timeout = timeout
        self.verbose = verbose

    # --------------------------------------------------------
    # CORE REQUEST
    # --------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> APIResponse:

        url = f"{self.base_url}{path}"

        if self.verbose:
            print(f"\n[HTTP] {method.upper()} {path}")

        try:
            start = time.perf_counter()

            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_body,
                timeout=self.timeout,
            )

            elapsed = (time.perf_counter() - start) * 1000.0

        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"\n[HTTP CONNECTION ERROR]\n"
                f"Não foi possível conectar à API em {self.base_url}\n"
                f"A API está rodando?\n"
                f"Erro: {e}"
            )

        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"\n[HTTP TIMEOUT]\n"
                f"Timeout ao chamar {url} ({self.timeout}s)"
            )

        if self.verbose:
            print(
                f"[HTTP] Status: {response.status_code} | "
                f"{elapsed:.1f} ms"
            )

            if response.status_code >= 400:
                print(f"[HTTP][ERROR BODY]: {response.text[:500]}")

        return APIResponse(
            status_code=response.status_code,
            elapsed_ms=elapsed,
            raw=response,
        )

    # --------------------------------------------------------
    # MÉTODOS PÚBLICOS
    # --------------------------------------------------------

    def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> APIResponse:
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> APIResponse:
        return self._request("POST", path, json_body=json_body)

    def put(
        self,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> APIResponse:
        return self._request("PUT", path, json_body=json_body)

    def delete(
        self,
        path: str,
    ) -> APIResponse:
        return self._request("DELETE", path)
    
    def patch(
            self,
            path: str,
            *,
            json_body: Optional[Dict[str, Any]] = None,
    ) -> APIResponse:
        return self._request("PATCH", path, json_body=json_body)

client = APIClient()
