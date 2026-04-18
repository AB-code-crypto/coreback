import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests


@dataclass
class MexcResponse:
    http_status: int
    payload: Any


class MexcClient:
    BASE_URL = "https://api.mexc.com"

    def __init__(self, timeout: int = 30, recv_window: int = 5000) -> None:
        self.timeout = timeout
        self.recv_window = recv_window

    def _build_url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    def _get(
            self,
            path: str,
            *,
            params: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
    ) -> MexcResponse:
        response = requests.get(
            self._build_url(path),
            params=params,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return MexcResponse(
            http_status=response.status_code,
            payload=response.json(),
        )

    def _sign_params(
            self,
            params: dict[str, Any],
            *,
            api_secret: str,
    ) -> dict[str, Any]:
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(
            api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            **params,
            "signature": signature,
        }

    def _get_private(
            self,
            path: str,
            *,
            api_key: str,
            api_secret: str,
            params: dict[str, Any] | None = None,
    ) -> MexcResponse:
        signed_params = {
            "timestamp": int(time.time() * 1000),
            "recvWindow": self.recv_window,
            **(params or {}),
        }
        signed_params = self._sign_params(signed_params, api_secret=api_secret)

        return self._get(
            path,
            params=signed_params,
            headers={
                "X-MEXC-APIKEY": api_key,
            },
        )

    # ------------------------------------------------------------------
    # Market data / public
    # ------------------------------------------------------------------

    def fetch_server_status(self) -> MexcResponse:
        return self._get("/api/v3/ping")

    def fetch_server_time(self) -> MexcResponse:
        return self._get("/api/v3/time")

    def fetch_default_symbols(self) -> MexcResponse:
        return self._get("/api/v3/defaultSymbols")

    def fetch_offline_symbols(self) -> MexcResponse:
        return self._get("/api/v3/symbol/offline")

    def fetch_exchange_info(
            self,
            *,
            symbol: str | None = None,
            symbols: list[str] | None = None,
    ) -> MexcResponse:
        params: dict[str, Any] = {}

        if symbol and symbols:
            raise ValueError("Передайте либо symbol, либо symbols, но не оба сразу.")

        if symbol:
            params["symbol"] = symbol

        if symbols:
            params["symbols"] = ",".join(symbols)

        return self._get("/api/v3/exchangeInfo", params=params or None)

    # ------------------------------------------------------------------
    # Wallet / private
    # ------------------------------------------------------------------

    def fetch_capital_config_getall(
            self,
            *,
            api_key: str,
            api_secret: str,
    ) -> MexcResponse:
        return self._get_private(
            "/api/v3/capital/config/getall",
            api_key=api_key,
            api_secret=api_secret,
        )

    # ------------------------------------------------------------------
    # Spot account / private
    # ------------------------------------------------------------------

    def fetch_trade_fee(
            self,
            *,
            api_key: str,
            api_secret: str,
            symbol: str,
    ) -> MexcResponse:
        return self._get_private(
            "/api/v3/tradeFee",
            api_key=api_key,
            api_secret=api_secret,
            params={"symbol": symbol},
        )
