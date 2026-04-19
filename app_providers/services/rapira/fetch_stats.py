from time import perf_counter

import requests
from django.utils import timezone

from app_core.models import PlatformSettings
from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.provider_stats import ProviderStats, ProviderStatsRequestStatus
from app_providers.services.rapira.client import RapiraClient


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


def _extract_pairs(payload) -> list[dict]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _pair_is_exchangeable(item: dict) -> bool:
    value = item.get("exchangeable")
    if isinstance(value, bool):
        return value
    if value in (1, "1"):
        return True
    if value in (0, "0"):
        return False
    return False


def _extract_market_rates_ok(payload) -> bool:
    if not isinstance(payload, dict):
        return False

    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return False

    code = payload.get("code")
    if code not in (0, "0", 200, "200", None):
        return False

    is_working = payload.get("isWorking")
    return is_working in (1, "1", True)


def _extract_server_time_ok(payload) -> bool:
    if not isinstance(payload, dict):
        return False
    value = payload.get("serverTime")
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def fetch_rapira_stats(provider: Provider) -> ProviderStats:
    if provider.code != ProviderCode.RAPIRA:
        raise ValueError("Этот сервис пока поддерживает только RAPIRA.")

    provider_api = _get_active_provider_api(provider)
    api_key = provider_api.get_api_key()
    api_secret = provider_api.get_api_secret()

    client = RapiraClient()
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
    stats_source = "rapira.private.market_pairs"
    stats_response_time_ms = None

    try:
        ping_started = perf_counter()
        ping_response = client.fetch_server_time()
        ping_response_time_ms = int((perf_counter() - ping_started) * 1000)
        ping_http_status = ping_response.http_status
        ping_success = _extract_server_time_ok(ping_response.payload)

        platform_started = perf_counter()
        market_rates_response = client.fetch_rates_json()
        platform_status_response_time_ms = int((perf_counter() - platform_started) * 1000)
        platform_status_http_status = market_rates_response.http_status
        platform_status_success = _extract_market_rates_ok(market_rates_response.payload)
        platform_status_code = 1 if platform_status_success else 0

        stats_started = perf_counter()
        pairs_response = client.fetch_pairs(api_key=api_key, api_secret=api_secret)
        stats_response_time_ms = int((perf_counter() - stats_started) * 1000)
        stats_http_status = pairs_response.http_status

        responded_at = timezone.now()

        pairs = _extract_pairs(pairs_response.payload)
        pairs = [item for item in pairs if _pair_is_exchangeable(item)]

        quote_asset_counts: dict[str, int] = {}
        for item in pairs:
            quote_code = item.get("baseSymbol")
            if not quote_code:
                continue
            quote_code = str(quote_code).upper()
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

        provider_is_available = ping_success and platform_status_success and bool(pairs)

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
            pairs_total=len(pairs),
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