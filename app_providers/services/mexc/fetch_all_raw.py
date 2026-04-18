from dataclasses import dataclass, field
from datetime import datetime

from django.utils import timezone

from app_providers.models.provider import Provider
from app_providers.services.mexc.client import MexcClient
from app_providers.services.raw_data_storage import save_raw_json_to_file


@dataclass
class MexcRawEndpointResult:
    name: str
    success: bool
    file_path: str
    http_status: int | None = None
    error_message: str = ""


@dataclass
class MexcRawDumpResult:
    requested_at: datetime
    responded_at: datetime
    items: list[MexcRawEndpointResult] = field(default_factory=list)

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


def fetch_mexc_all_raw(provider: Provider) -> MexcRawDumpResult:
    provider_api = _get_active_provider_api(provider)
    client = MexcClient()
    requested_at = timezone.now()

    api_key = provider_api.get_api_key()
    api_secret = provider_api.get_api_secret()

    endpoint_calls = [
        ("server_status", lambda: client.fetch_server_status()),
        ("server_time", lambda: client.fetch_server_time()),
        ("default_symbols", lambda: client.fetch_default_symbols()),
        ("offline_symbols", lambda: client.fetch_offline_symbols()),
        ("exchange_info", lambda: client.fetch_exchange_info()),
        ("capital_config_getall", lambda: client.fetch_capital_config_getall(api_key=api_key, api_secret=api_secret)),
        ("trade_fee_btcusdt", lambda: client.fetch_trade_fee(api_key=api_key, api_secret=api_secret, symbol="BTCUSDT")),
        ("deposit_history", lambda: client.fetch_deposit_history(api_key=api_key, api_secret=api_secret)),
        ("withdraw_history", lambda: client.fetch_withdraw_history(api_key=api_key, api_secret=api_secret)),
    ]

    items: list[MexcRawEndpointResult] = []

    for request_type, fetcher in endpoint_calls:
        try:
            response = fetcher()
            file_path = _save_single_payload(
                provider_code=provider.code,
                request_type=request_type,
                payload=response.payload,
            )

            items.append(
                MexcRawEndpointResult(
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
                MexcRawEndpointResult(
                    name=request_type,
                    success=False,
                    file_path=file_path,
                    http_status=None,
                    error_message=str(exc),
                )
            )

    responded_at = timezone.now()

    return MexcRawDumpResult(
        requested_at=requested_at,
        responded_at=responded_at,
        items=items,
    )
