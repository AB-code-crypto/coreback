from dataclasses import dataclass, field
from datetime import datetime

from django.utils import timezone

from app_providers.models.provider import Provider
from app_providers.services.rapira.client import RapiraClient
from app_providers.services.raw_data_storage import save_raw_json_to_file


@dataclass
class RapiraRawEndpointResult:
    name: str
    success: bool
    file_path: str
    http_status: int | None = None
    error_message: str = ""


@dataclass
class RapiraRawDumpResult:
    requested_at: datetime
    responded_at: datetime
    items: list[RapiraRawEndpointResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for item in self.items if item.success)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if not item.success)

    @property
    def total_count(self) -> int:
        return len(self.items)


def _get_active_provider_api(provider):
    provider_api = (
        provider.apis
        .filter(is_active=True)
        .order_by("priority", "id")
        .first()
    )
    if not provider_api:
        raise ValueError("У провайдера нет активного API-набора.")
    if not provider_api.has_api_key():
        raise ValueError("У активного API-набора не заполнен api_key.")
    if not provider_api.has_api_secret():
        raise ValueError("У активного API-набора не заполнен api_secret.")
    return provider_api


def _save_single_payload(provider_code: str, request_type: str, payload: object) -> str:
    return save_raw_json_to_file(
        provider_code=provider_code,
        request_type=request_type,
        payload=payload,
    )


def fetch_rapira_all_raw(provider: Provider) -> RapiraRawDumpResult:
    provider_api = _get_active_provider_api(provider)
    client = RapiraClient()

    requested_at = timezone.now()

    api_key = provider_api.get_api_key()
    api_secret = provider_api.get_api_secret()

    endpoint_calls = [
        ("server_time", lambda: client.fetch_server_time()),
        ("market_rates", lambda: client.fetch_rates_json()),
        ("available_token_settings", lambda: client.fetch_available_token_settings(api_key=api_key, api_secret=api_secret, )),
        ("market_pairs", lambda: client.fetch_pairs(api_key=api_key, api_secret=api_secret)),
        ("token", lambda: client.fetch_tokens(api_key=api_key, api_secret=api_secret)),
        ("spot_fees", lambda: client.fetch_spot_fees(api_key=api_key, api_secret=api_secret)),
        ("balances", lambda: client.fetch_balances(api_key=api_key, api_secret=api_secret)),
        ("frozen_balances", lambda: client.fetch_frozen_balances(api_key=api_key, api_secret=api_secret)),
        # Может упасть, если ключ без WITHDRAW-прав. Это нормально: raw-дамп сохранит ошибку.
        (
            "withdraw_crypto_history",
            lambda: client.fetch_withdraw_crypto_history(
                api_key=api_key,
                api_secret=api_secret,
                page_no=1,
                page_size=100,
            ),
        ),
    ]

    items: list[RapiraRawEndpointResult] = []

    for request_type, fetcher in endpoint_calls:
        try:
            response = fetcher()
            file_path = _save_single_payload(
                provider_code=provider.code,
                request_type=request_type,
                payload=response.payload,
            )
            items.append(
                RapiraRawEndpointResult(
                    name=request_type,
                    success=True,
                    file_path=file_path,
                    http_status=response.http_status,
                    error_message="",
                )
            )
        except Exception as exc:
            error_payload = {
                "error": str(exc),
                "request_type": request_type,
            }
            file_path = _save_single_payload(
                provider_code=provider.code,
                request_type=request_type,
                payload=error_payload,
            )
            items.append(
                RapiraRawEndpointResult(
                    name=request_type,
                    success=False,
                    file_path=file_path,
                    http_status=None,
                    error_message=str(exc),
                )
            )

    responded_at = timezone.now()
    return RapiraRawDumpResult(
        requested_at=requested_at,
        responded_at=responded_at,
        items=items,
    )
