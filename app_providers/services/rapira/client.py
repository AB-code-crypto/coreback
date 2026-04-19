import base64
import secrets
import time
from dataclasses import dataclass

import jwt
import requests


@dataclass
class RapiraResponse:
    payload: object
    http_status: int


class RapiraClient:
    BASE_URL = "https://api.rapira.net"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self._bearer_token: str | None = None
        self._bearer_token_expires_at: float = 0.0

    def _normalize_private_key(self, value: str) -> str:
        raw = (value or "").strip()
        if not raw:
            raise ValueError("Rapira private key is empty.")

        raw = raw.replace("\\n", "\n")
        if "BEGIN" in raw:
            return raw

        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8")
            decoded = decoded.replace("\\n", "\n")
            if "BEGIN" in decoded:
                return decoded
        except Exception:
            pass

        return raw

    def _request(
            self,
            method: str,
            path: str,
            *,
            params: dict | None = None,
            json_data: dict | None = None,
            headers: dict | None = None,
    ) -> RapiraResponse:
        url = f"{self.BASE_URL}{path}"
        request_headers = {
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=request_headers,
            timeout=self.timeout,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body_preview = ""
            if exc.response is not None:
                body_preview = exc.response.text[:500]
            raise requests.HTTPError(f"{exc}; response={body_preview}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        return RapiraResponse(
            payload=payload,
            http_status=response.status_code,
        )

    def _build_client_jwt(self, private_key: str, ttl_seconds: int = 3600) -> str:
        payload = {
            "exp": int(time.time()) + ttl_seconds,
            "jti": secrets.token_hex(12),
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    def _get_bearer_token(self, api_key: str, api_secret: str) -> str:
        now = time.time()
        if self._bearer_token and now < self._bearer_token_expires_at:
            return self._bearer_token

        private_key = self._normalize_private_key(api_secret)
        client_jwt = self._build_client_jwt(private_key=private_key)

        response = self._request(
            "POST",
            "/open/generate_jwt",
            json_data={
                "kid": api_key,
                "jwt_token": client_jwt,
            },
        )

        payload = response.payload
        if not isinstance(payload, dict):
            raise ValueError("Rapira generate_jwt returned non-dict payload.")

        token = payload.get("token")
        if not token:
            raise ValueError(f"Rapira generate_jwt returned no token: {payload!r}")

        self._bearer_token = str(token)
        # Консервативный кеш, чтобы не дёргать generate_jwt на каждый запрос,
        # но и не полагаться на неизвестный TTL ключа.
        self._bearer_token_expires_at = now + (25 * 60)
        return self._bearer_token

    def _authorized_headers(self, api_key: str, api_secret: str) -> dict:
        token = self._get_bearer_token(api_key=api_key, api_secret=api_secret)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def _get_private(
            self,
            path: str,
            *,
            api_key: str,
            api_secret: str,
            params: dict | None = None,
    ) -> RapiraResponse:
        return self._request(
            "GET",
            path,
            params=params,
            headers=self._authorized_headers(api_key=api_key, api_secret=api_secret),
        )

    def fetch_server_time(self) -> RapiraResponse:
        return self._request("GET", "/open/system/time")

    def fetch_rates_json(self) -> RapiraResponse:
        return self._request("GET", "/open/market/rates")

    def fetch_available_token_settings(self) -> RapiraResponse:
        return self._request("GET", "/open/crypto-processing/token-settings/available")

    def fetch_pairs(self, *, api_key: str, api_secret: str) -> RapiraResponse:
        return self._get_private(
            "/open/market/pairs",
            api_key=api_key,
            api_secret=api_secret,
        )

    def fetch_tokens(self, *, api_key: str, api_secret: str) -> RapiraResponse:
        return self._get_private(
            "/open/token",
            api_key=api_key,
            api_secret=api_secret,
        )

    def fetch_spot_fees(self, *, api_key: str, api_secret: str) -> RapiraResponse:
        return self._get_private(
            "/open/my-spot-fee",
            api_key=api_key,
            api_secret=api_secret,
        )

    def fetch_balances(self, *, api_key: str, api_secret: str) -> RapiraResponse:
        return self._get_private(
            "/open/wallet/balance",
            api_key=api_key,
            api_secret=api_secret,
        )

    def fetch_frozen_balances(self, *, api_key: str, api_secret: str) -> RapiraResponse:
        return self._get_private(
            "/open/wallet/balance/frozen",
            api_key=api_key,
            api_secret=api_secret,
        )

    def fetch_withdraw_crypto_history(
            self,
            *,
            api_key: str,
            api_secret: str,
            page_no: int = 1,
            page_size: int = 100,
    ) -> RapiraResponse:
        return self._get_private(
            "/open/withdraw/crypto/history",
            api_key=api_key,
            api_secret=api_secret,
            params={
                "pageNo": page_no,
                "pageSize": page_size,
            },
        )
