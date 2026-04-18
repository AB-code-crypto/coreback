from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app_providers.models.provider_api import ProviderApi
from app_providers.services.whitebit.client import WhitebitClient


@dataclass
class SyncProviderApiFeesResult:
    updated: bool
    spot_maker_fee: Decimal
    spot_taker_fee: Decimal
    futures_maker_fee: Decimal
    futures_taker_fee: Decimal


def _require_dict(value, path: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be dict, got {type(value).__name__}")
    return value


def _to_decimal_percent(value, path: str) -> Decimal:
    if value in (None, ""):
        raise ValueError(f"{path} is empty")

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be a decimal-compatible value, got {value!r}") from exc


def _percent_to_fraction(value: Decimal) -> Decimal:
    return value / Decimal("100")


def sync_whitebit_provider_api_fees(provider_api: ProviderApi) -> SyncProviderApiFeesResult:
    if not provider_api.has_api_key():
        raise ValueError("У выбранного API-набора не заполнен api_key.")

    if not provider_api.has_api_secret():
        raise ValueError("У выбранного API-набора не заполнен api_secret.")

    client = WhitebitClient()
    response = client.fetch_all_market_fees(
        api_key=provider_api.get_api_key(),
        api_secret=provider_api.get_api_secret(),
    )

    payload = _require_dict(response.payload, "market_fee")

    for key in ("maker", "taker", "futures_maker", "futures_taker"):
        if key not in payload:
            raise KeyError(f"Missing key: market_fee.{key}")

    spot_maker_fee = _percent_to_fraction(_to_decimal_percent(payload["maker"], "market_fee.maker"))
    spot_taker_fee = _percent_to_fraction(_to_decimal_percent(payload["taker"], "market_fee.taker"))
    futures_maker_fee = _percent_to_fraction(_to_decimal_percent(payload["futures_maker"], "market_fee.futures_maker"))
    futures_taker_fee = _percent_to_fraction(_to_decimal_percent(payload["futures_taker"], "market_fee.futures_taker"))

    updated = False

    if provider_api.spot_maker_fee != spot_maker_fee:
        provider_api.spot_maker_fee = spot_maker_fee
        updated = True

    if provider_api.spot_taker_fee != spot_taker_fee:
        provider_api.spot_taker_fee = spot_taker_fee
        updated = True

    if provider_api.futures_maker_fee != futures_maker_fee:
        provider_api.futures_maker_fee = futures_maker_fee
        updated = True

    if provider_api.futures_taker_fee != futures_taker_fee:
        provider_api.futures_taker_fee = futures_taker_fee
        updated = True

    if updated:
        provider_api.save(update_fields=[
            "spot_maker_fee",
            "spot_taker_fee",
            "futures_maker_fee",
            "futures_taker_fee",
            "updated_at",
        ])

    return SyncProviderApiFeesResult(
        updated=updated,
        spot_maker_fee=spot_maker_fee,
        spot_taker_fee=spot_taker_fee,
        futures_maker_fee=futures_maker_fee,
        futures_taker_fee=futures_taker_fee,
    )
