import base64
import json
import os
import secrets
import subprocess
import tempfile
import time
from dataclasses import dataclass

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

    @staticmethod
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _decode_private_key_bytes(self, value: str) -> bytes:
        raw = (value or "").strip()
        if not raw:
            raise ValueError("Rapira private key is empty.")

        # Если ключ уже хранится как PEM-текст
        if "BEGIN " in raw:
            return raw.encode("utf-8")

        # Обычный для вас случай: в БД лежит base64-строка PEM
        compact = "".join(raw.split())
        try:
            return base64.b64decode(compact, validate=False)
        except Exception as exc:
            raise ValueError("Rapira private key is not valid base64.") from exc

    def _build_client_jwt(self, private_key_bytes: bytes, ttl_seconds: int = 3600) -> str:
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "exp": int(time.time()) + ttl_seconds,
            "jti": secrets.token_hex(12),
        }

        header_b64 = self._b64url(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_b64 = self._b64url(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(private_key_bytes)
                tmp_path = tmp.name

            os.chmod(tmp_path, 0o600)

            result = subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", tmp_path],
                input=signing_input,
                capture_output=True,
                check=True,
                timeout=self.timeout,
            )

            signature_b64 = self._b64url(result.stdout)
            return f"{header_b64}.{payload_b64}.{signature_b64}"

        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            raise ValueError(f"OpenSSL signing failed: {stderr or exc}") from exc

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

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
                body_preview = exc.response.text[:1000]
            raise requests.HTTPError(f"{exc}; response={body_preview}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        return RapiraResponse(
            payload=payload,
            http_status=response.status_code,
        )

    def _get_bearer_token(self, api_key: str, api_secret: str) -> str:
        now = time.time()
        if self._bearer_token and now < self._bearer_token_expires_at:
            return self._bearer_token

        private_key_bytes = self._decode_private_key_bytes(api_secret)
        client_jwt = self._build_client_jwt(private_key_bytes=private_key_bytes)

        response = self._request(
            "POST",
            "/open/generate_jwt",
            json_data={
                "kid": api_key,
                "jwt_token": client_jwt,
            },
            headers={
                "Content-Type": "application/json",
            },
        )

        payload = response.payload
        if not isinstance(payload, dict):
            raise ValueError("Rapira generate_jwt returned non-dict payload.")

        token = payload.get("token")
        if not token:
            raise ValueError(f"Rapira generate_jwt returned no token: {payload!r}")

        self._bearer_token = str(token)
        # Консервативный кеш bearer-токена
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

    def fetch_available_token_settings(self, *, api_key: str, api_secret: str) -> RapiraResponse:
        return self._get_private(
            "/open/crypto-processing/token-settings/available",
            api_key=api_key,
            api_secret=api_secret,
        )

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
