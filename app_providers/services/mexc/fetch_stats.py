from time import perf_counter

import requests
from django.utils import timezone

from app_core.models import PlatformSettings
from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.provider_stats import ProviderStats, ProviderStatsRequestStatus
from app_providers.services.mexc.client import MexcClient


def _get_stablecoin_codes() -> set[str]:
    settings_obj = PlatformSettings.objects.first()
    if settings_obj:
        return set(settings_obj.get_stablecoin_codes())
    return set()


def _get_fiat_codes() -> set[str]:
    settings_obj = PlatformSettings.objects.first()
    if settings_obj:
        return set(settings_obj.get_fiat_currency_codes())
    return set()


def _extract_default_symbols_ok(payload) -> bool:
    if not isinstance(payload, dict):
        return False

    if "code" not in payload:
        return False
    if "data" not in payload:
        return False

    if payload["code"] != 200:
        return False

    return isinstance(payload["data"], list)


def _extract_default_symbols_code(payload) -> int | None:
    if not isinstance(payload, dict):
        return None

    code = payload.get("code")
    if code in (None, ""):
        return None

    try:
        return int(code)
    except (TypeError, ValueError):
        return None


def _extract_exchange_symbols(payload) -> list[dict]:
    if not isinstance(payload, dict):
        return []

    symbols = payload.get("symbols")
    if not isinstance(symbols, list):
        return []

    return [item for item in symbols if isinstance(item, dict)]


def _is_spot_symbol_enabled(item: dict) -> bool:
    if "isSpotTradingAllowed" in item:
        return bool(item["isSpotTradingAllowed"])

    permissions = item.get("permissions")
    if isinstance(permissions, list):
        return "SPOT" in permissions

    return True


def fetch_mexc_stats(provider: Provider) -> ProviderStats:
    if provider.code != ProviderCode.MEXC:
        raise ValueError("Этот сервис пока поддерживает только MEXC.")

    client = MexcClient()
    stablecoin_codes = _get_stablecoin_codes()
    fiat_codes_master = _get_fiat_codes()

    requested_at = timezone.now()

    ping_http_status = None
    ping_success = False
    ping_response_time_ms = None

    platform_status_http_status = None
    platform_status_success = False
    platform_status_code = None
    platform_status_response_time_ms = None

    stats_http_status = None
    stats_source = "mexc.public.exchange_info"
    stats_response_time_ms = None

    try:
        ping_started = perf_counter()
        ping_response = client.fetch_server_status()
        ping_response_time_ms = int((perf_counter() - ping_started) * 1000)
        ping_http_status = ping_response.http_status
        ping_success = ping_response.payload == {}

        platform_started = perf_counter()
        default_symbols_response = client.fetch_default_symbols()
        platform_status_response_time_ms = int((perf_counter() - platform_started) * 1000)
        platform_status_http_status = default_symbols_response.http_status

        platform_status_success = _extract_default_symbols_ok(default_symbols_response.payload)
        platform_status_code = _extract_default_symbols_code(default_symbols_response.payload)

        stats_started = perf_counter()
        exchange_info_response = client.fetch_exchange_info()
        stats_response_time_ms = int((perf_counter() - stats_started) * 1000)
        stats_http_status = exchange_info_response.http_status

        responded_at = timezone.now()

        symbols = _extract_exchange_symbols(exchange_info_response.payload)
        symbols = [item for item in symbols if _is_spot_symbol_enabled(item)]

        quote_asset_counts: dict[str, int] = {}

        for item in symbols:
            base_code = item.get("baseAsset")
            quote_code = item.get("quoteAsset")

            if not base_code or not quote_code:
                continue

            quote_code = str(quote_code)
            quote_asset_counts[quote_code] = quote_asset_counts.get(quote_code, 0) + 1

        stablecoin_pair_counts = {
            code: count
            for code, count in sorted(
                (
                    (code, quote_asset_counts[code])
                    for code in quote_asset_counts
                    if code in stablecoin_codes
                ),
                key=lambda x: (-x[1], x[0]),
            )
        }

        found_fiats = [
            code
            for code, _count in sorted(
                (
                    (code, quote_asset_counts[code])
                    for code in quote_asset_counts
                    if code in fiat_codes_master
                ),
                key=lambda x: (-x[1], x[0]),
            )
        ]

        provider_is_available = ping_success and platform_status_success

        return ProviderStats.objects.create(
            provider=provider,
            request_status=ProviderStatsRequestStatus.SUCCESS,
            requested_at=requested_at,
            responded_at=responded_at,
            provider_is_available=provider_is_available,
            error_message="",
            ping_http_status=ping_http_status,
            ping_success=ping_success,
            ping_response_time_ms=ping_response_time_ms,
            platform_status_http_status=platform_status_http_status,
            platform_status_success=platform_status_success,
            platform_status_code=platform_status_code,
            platform_status_response_time_ms=platform_status_response_time_ms,
            stats_http_status=stats_http_status,
            stats_source=stats_source,
            stats_response_time_ms=stats_response_time_ms,
            pairs_total=len(symbols),
            quote_assets_total=len(quote_asset_counts),
            quote_asset_counts=quote_asset_counts,
            stablecoin_pair_counts=stablecoin_pair_counts,
            fiat_codes=found_fiats,
        )

    except requests.Timeout as exc:
        responded_at = timezone.now()

        return ProviderStats.objects.create(
            provider=provider,
            request_status=ProviderStatsRequestStatus.TIMEOUT,
            requested_at=requested_at,
            responded_at=responded_at,
            provider_is_available=False,
            error_message=str(exc),
            ping_http_status=ping_http_status,
            ping_success=ping_success,
            ping_response_time_ms=ping_response_time_ms,
            platform_status_http_status=platform_status_http_status,
            platform_status_success=platform_status_success,
            platform_status_code=platform_status_code,
            platform_status_response_time_ms=platform_status_response_time_ms,
            stats_http_status=stats_http_status,
            stats_source=stats_source,
            stats_response_time_ms=stats_response_time_ms,
        )

    except Exception as exc:
        responded_at = timezone.now()

        return ProviderStats.objects.create(
            provider=provider,
            request_status=ProviderStatsRequestStatus.FAILED,
            requested_at=requested_at,
            responded_at=responded_at,
            provider_is_available=False,
            error_message=str(exc),
            ping_http_status=ping_http_status,
            ping_success=ping_success,
            ping_response_time_ms=ping_response_time_ms,
            platform_status_http_status=platform_status_http_status,
            platform_status_success=platform_status_success,
            platform_status_code=platform_status_code,
            platform_status_response_time_ms=platform_status_response_time_ms,
            stats_http_status=stats_http_status,
            stats_source=stats_source,
            stats_response_time_ms=stats_response_time_ms,
        )
