import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class WhitebitResponse:
    http_status: int
    payload: Any


class WhitebitClient:
    BASE_URL = "https://whitebit.com"

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def _build_url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    def _get(
            self,
            path: str,
            *,
            params: dict[str, Any] | None = None,
    ) -> WhitebitResponse:
        response = requests.get(
            self._build_url(path),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return WhitebitResponse(
            http_status=response.status_code,
            payload=response.json(),
        )

    def _post_private(
            self,
            path: str,
            *,
            api_key: str,
            api_secret: str,
            body: dict[str, Any] | None = None,
            params: dict[str, Any] | None = None,
    ) -> WhitebitResponse:
        request_body = {
            "request": path,
            "nonce": str(int(time.time() * 1000)),
            "nonceWindow": True,
            **(body or {}),
        }

        request_body_json = json.dumps(
            request_body,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        payload_b64 = base64.b64encode(
            request_body_json.encode("utf-8")
        ).decode("ascii")

        signature = hmac.new(
            api_secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

        response = requests.post(
            self._build_url(path),
            params=params,
            data=request_body_json,
            headers={
                "Content-Type": "application/json",
                "X-TXC-APIKEY": api_key,
                "X-TXC-PAYLOAD": payload_b64,
                "X-TXC-SIGNATURE": signature,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        return WhitebitResponse(
            http_status=response.status_code,
            payload=response.json(),
        )

    # ------------------------------------------------------------------
    # Market Data / Server & Status
    # ------------------------------------------------------------------

    def fetch_server_status(self) -> WhitebitResponse:
        return self._get("/api/v4/public/ping")

    def fetch_server_time(self) -> WhitebitResponse:
        return self._get("/api/v4/public/time")

    def fetch_maintenance_status(self) -> WhitebitResponse:
        return self._get("/api/v4/public/platform/status")

    # ------------------------------------------------------------------
    # Market Data / Fees & Funding
    # ------------------------------------------------------------------

    def fetch_public_fee(self) -> WhitebitResponse:
        return self._get("/api/v4/public/fee")

    # ------------------------------------------------------------------
    # Spot Trading / Market Fee
    # ------------------------------------------------------------------

    def fetch_market_fee(
            self,
            *,
            api_key: str,
            api_secret: str,
            market: str | None = None,
    ) -> WhitebitResponse:
        params = {"market": market} if market else None

        return self._post_private(
            "/api/v4/market/fee",
            api_key=api_key,
            api_secret=api_secret,
            params=params,
        )

    def fetch_all_market_fees(
            self,
            *,
            api_key: str,
            api_secret: str,
    ) -> WhitebitResponse:
        return self._post_private(
            "/api/v4/market/fee",
            api_key=api_key,
            api_secret=api_secret,
        )

    # ------------------------------------------------------------------
    # Market Data / Markets & Assets
    # ------------------------------------------------------------------

    def fetch_market_info(self) -> WhitebitResponse:
        return self._get("/api/v4/public/markets")

    def fetch_market_activity(self) -> WhitebitResponse:
        return self._get("/api/v4/public/ticker")

    def fetch_asset_status_list(self) -> WhitebitResponse:
        return self._get("/api/v4/public/assets")

    def fetch_symbols(self) -> WhitebitResponse:
        return self._get("/api/v1/public/symbols")

    # ------------------------------------------------------------------
    # Account & Wallet / Get fees
    # ------------------------------------------------------------------

    def fetch_account_fees(
            self,
            *,
            api_key: str,
            api_secret: str,
    ) -> WhitebitResponse:
        return self._post_private(
            "/api/v4/main-account/fee",
            api_key=api_key,
            api_secret=api_secret,
        )
