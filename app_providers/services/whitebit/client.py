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

    def _get(self, path: str) -> WhitebitResponse:
        url = f"{self.BASE_URL}{path}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return WhitebitResponse(
            http_status=response.status_code,
            payload=response.json(),
        )

    def fetch_assets(self) -> WhitebitResponse:
        return self._get("/api/v4/public/assets")
