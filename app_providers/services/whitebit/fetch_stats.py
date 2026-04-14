from time import perf_counter

import requests
from django.utils import timezone

from app_core.models import PlatformSettings
from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.provider_stats import (
    ProviderStats,
    ProviderStatsRequestStatus,
)
from app_providers.services.whitebit.client import WhitebitClient


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


def _extract_markets(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("result", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

    return []


def _extract_market_codes(markets: list[dict]) -> list[str]:
    result = []

    for item in markets:
        if not isinstance(item, dict):
            continue

        code = (
                item.get("name")
                or item.get("ticker_id")
                or item.get("market")
                or item.get("symbol")
        )
        if code:
            result.append(str(code))

    return result


def _split_market_code(code: str):
    if "_" in code:
        return code.split("_", 1)

    if "/" in code:
        return code.split("/", 1)

    return None, None


def fetch_whitebit_stats(provider: Provider) -> ProviderStats:
    if provider.code != ProviderCode.WHITEBIT:
        raise ValueError("Этот сервис пока поддерживает только WHITEBIT.")

    client = WhitebitClient()
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
    stats_source = "whitebit.public.markets"
    stats_response_time_ms = None

    try:
        ping_started = perf_counter()
        ping_response = client.fetch_ping()
        ping_response_time_ms = int((perf_counter() - ping_started) * 1000)
        ping_http_status = ping_response.http_status
        ping_success = ping_response.payload == ["pong"]

        platform_started = perf_counter()
        platform_response = client.fetch_platform_status()
        platform_status_response_time_ms = int((perf_counter() - platform_started) * 1000)
        platform_status_http_status = platform_response.http_status

        if isinstance(platform_response.payload, dict):
            platform_status_code = platform_response.payload.get("status")

        platform_status_success = platform_status_code == 1

        stats_started = perf_counter()
        markets_response = client.fetch_markets()
        stats_response_time_ms = int((perf_counter() - stats_started) * 1000)
        stats_http_status = markets_response.http_status

        responded_at = timezone.now()

        markets = _extract_markets(markets_response.payload)
        market_codes = _extract_market_codes(markets)

        quote_asset_counts: dict[str, int] = {}
        # base_asset_counts: dict[str, int] = {}

        for market_code in market_codes:
            base_code, quote_code = _split_market_code(market_code)
            if not base_code or not quote_code:
                continue

            quote_asset_counts[quote_code] = quote_asset_counts.get(quote_code, 0) + 1
            # base_asset_counts[base_code] = base_asset_counts.get(base_code, 0) + 1

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

        provider_is_available = (
                ping_success
                and platform_status_success
                and platform_status_code == 1
        )

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
            pairs_total=len(market_codes),
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
