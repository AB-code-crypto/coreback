from dataclasses import dataclass, field
from datetime import datetime

from django.utils import timezone

from app_providers.models.provider import Provider, ProviderCode
from app_providers.services.raw_data_storage import save_raw_json_to_file
from app_providers.services.whitebit.client import WhitebitClient


@dataclass
class WhitebitRawEndpointResult:
    name: str
    success: bool
    file_path: str
    http_status: int | None = None
    error_message: str = ""


@dataclass
class WhitebitRawDumpResult:
    requested_at: datetime
    responded_at: datetime
    items: list[WhitebitRawEndpointResult] = field(default_factory=list)

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


def fetch_whitebit_all_raw(provider: Provider) -> WhitebitRawDumpResult:
    if provider.code != ProviderCode.WHITEBIT:
        raise ValueError("Этот сервис пока поддерживает только WHITEBIT.")

    provider_api = _get_active_provider_api(provider)
    client = WhitebitClient()
    requested_at = timezone.now()

    api_key = provider_api.get_api_key()
    api_secret = provider_api.get_api_secret()

    # market сейчас в docs optional и ignored,
    # но отдельный вызов всё равно оставляем для отдельного файла.
    endpoint_calls = [
        ("server_status", lambda: client.fetch_server_status()),
        ("server_time", lambda: client.fetch_server_time()),
        ("maintenance_status", lambda: client.fetch_maintenance_status()),
        ("public_fee", lambda: client.fetch_public_fee()),
        ("market_fee", lambda: client.fetch_market_fee(
            api_key=api_key,
            api_secret=api_secret,
            market="BTC_USDT",
        )),
        ("all_market_fees", lambda: client.fetch_all_market_fees(
            api_key=api_key,
            api_secret=api_secret,
        )),
        ("market_info", lambda: client.fetch_market_info()),
        ("market_activity", lambda: client.fetch_market_activity()),
        ("asset_status_list", lambda: client.fetch_asset_status_list()),
        ("symbols", lambda: client.fetch_symbols()),
        ("account_fees", lambda: client.fetch_account_fees(
            api_key=api_key,
            api_secret=api_secret,
        )),
    ]

    items: list[WhitebitRawEndpointResult] = []

    for request_type, fetcher in endpoint_calls:
        try:
            response = fetcher()
            file_path = _save_single_payload(
                provider_code=provider.code,
                request_type=request_type,
                payload=response.payload,
            )

            items.append(
                WhitebitRawEndpointResult(
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
                WhitebitRawEndpointResult(
                    name=request_type,
                    success=False,
                    file_path=file_path,
                    http_status=None,
                    error_message=str(exc),
                )
            )

    responded_at = timezone.now()

    return WhitebitRawDumpResult(
        requested_at=requested_at,
        responded_at=responded_at,
        items=items,
    )
