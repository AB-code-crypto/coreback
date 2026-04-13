from time import perf_counter

from django.utils import timezone

from app_core.models import PlatformSettings
from app_providers.models import ProviderStats
from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.provider_stats import ProviderStatsRequestStatus
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
        # на случай, если провайдер завернёт список в result/data
        for key in ("result", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _extract_market_codes(markets: list[dict]) -> list[str]:
    codes = []

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
            codes.append(str(code))

    return codes


def _split_market_code(code: str):
    if "_" in code:
        parts = code.split("_", 1)
        return parts[0], parts[1]

    if "/" in code:
        parts = code.split("/", 1)
        return parts[0], parts[1]

    return None, None


def fetch_whitebit_stats(provider: Provider) -> ProviderStats:
    if provider.code != ProviderCode.WHITEBIT:
        raise ValueError("fetch_whitebit_stats supports only WHITEBIT.")

    client = WhitebitClient()

    requested_at = timezone.now()
    started = perf_counter()

    try:
        ping_response = client.fetch_ping()
        ping_ok = ping_response.payload == ["pong"]

        markets_response = client.fetch_markets()

        responded_at = timezone.now()
        response_time_ms = int((perf_counter() - started) * 1000)

        markets = _extract_markets(markets_response.payload)
        market_codes = _extract_market_codes(markets)

        stablecoin_codes = _get_stablecoin_codes()
        fiat_codes_master = _get_fiat_codes()

        quote_asset_counts: dict[str, int] = {}
        base_asset_counts: dict[str, int] = {}

        for market_code in market_codes:
            base_code, quote_code = _split_market_code(market_code)
            if not base_code or not quote_code:
                continue

            quote_asset_counts[quote_code] = quote_asset_counts.get(quote_code, 0) + 1
            base_asset_counts[base_code] = base_asset_counts.get(base_code, 0) + 1

        active_stablecoins = sorted(
            [code for code in quote_asset_counts.keys() if code in stablecoin_codes]
        )
        stablecoin_pair_counts = {
            code: quote_asset_counts[code]
            for code in active_stablecoins
        }
        found_fiats = sorted(
            [code for code in quote_asset_counts.keys() if code in fiat_codes_master]
        )

        top_quote_assets = [
            code
            for code, _count in sorted(
                quote_asset_counts.items(),
                key=lambda x: (-x[1], x[0]),
            )[:10]
        ]
        top_base_assets = [
            code
            for code, _count in sorted(
                base_asset_counts.items(),
                key=lambda x: (-x[1], x[0]),
            )[:10]
        ]

        return ProviderStats.objects.create(
            provider=provider,
            request_status=ProviderStatsRequestStatus.SUCCESS,
            requested_at=requested_at,
            responded_at=responded_at,
            response_time_ms=response_time_ms,
            http_status=markets_response.http_status,
            source="whitebit.public.ping+markets",
            provider_is_available=ping_ok,
            error_message="",
            pairs_total=len(market_codes),
            quote_assets_total=len(quote_asset_counts),
            stablecoins_total=len(active_stablecoins),
            quote_asset_counts=quote_asset_counts,
            stablecoin_pair_counts=stablecoin_pair_counts,
            active_stablecoins=active_stablecoins,
            fiat_codes=found_fiats,
            top_quote_assets=top_quote_assets,
            top_base_assets=top_base_assets,
        )

    except requests.Timeout as exc:
        responded_at = timezone.now()
        response_time_ms = int((perf_counter() - started) * 1000)

        return ProviderStats.objects.create(
            provider=provider,
            request_status=ProviderStatsRequestStatus.TIMEOUT,
            requested_at=requested_at,
            responded_at=responded_at,
            response_time_ms=response_time_ms,
            http_status=None,
            source="whitebit.public.ping+markets",
            provider_is_available=False,
            error_message=str(exc),
        )

    except Exception as exc:
        responded_at = timezone.now()
        response_time_ms = int((perf_counter() - started) * 1000)

        return ProviderStats.objects.create(
            provider=provider,
            request_status=ProviderStatsRequestStatus.FAILED,
            requested_at=requested_at,
            responded_at=responded_at,
            response_time_ms=response_time_ms,
            http_status=None,
            source="whitebit.public.ping+markets",
            provider_is_available=False,
            error_message=str(exc),
        )
