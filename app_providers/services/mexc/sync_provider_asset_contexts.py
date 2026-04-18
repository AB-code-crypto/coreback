import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app_core.models import PlatformSettings
from app_providers.models.provider import Provider
from app_providers.models.provider_asset_context import (
    ProviderAssetContext,
    ProviderAssetContextMatchStatus,
)
from app_providers.services.raw_data_storage import get_raw_full_path


@dataclass
class SyncCounters:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    skipped_inactive_assets: int = 0


def _load_raw_json(provider_code: str, request_type: str):
    path = get_raw_full_path(provider_code, request_type)
    if not path.exists():
        raise FileNotFoundError(
            f"Raw JSON не найден: storage/raw/{provider_code}/{request_type}.json"
        )

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _get_stablecoin_codes() -> set[str]:
    settings_obj = PlatformSettings.objects.first()
    if settings_obj:
        return set(settings_obj.get_stablecoin_codes())
    return set()


def _require_dict(value, path: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be dict, got {type(value).__name__}")
    return value


def _require_list(value, path: str) -> list:
    if not isinstance(value, list):
        raise TypeError(f"{path} must be list, got {type(value).__name__}")
    return value


def _to_non_negative_int_zero(value) -> int:
    if value in (None, ""):
        return 0

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Cannot convert to int: {value!r}")

    return max(0, parsed)


def _to_decimal(value, path: str) -> Decimal:
    if value in (None, ""):
        raise ValueError(f"{path} is empty")

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be decimal-compatible, got {value!r}") from exc


def _to_decimal_or_none(value, path: str):
    if value in (None, ""):
        return None
    return _to_decimal(value, path)


def _to_precision(value, path: str, default: int = 8) -> int:
    if value in (None, ""):
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{path} must be int-compatible, got {value!r}")

    return max(0, parsed)


def _to_bool(value, path: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{path} must be bool, got {type(value).__name__}")
    return value


def _decimal_fits_model_field(model_cls, field_name: str, value: Decimal) -> bool:
    field = model_cls._meta.get_field(field_name)
    max_digits = field.max_digits
    decimal_places = field.decimal_places

    sign, digits, exponent = value.as_tuple()
    digits_count = len(digits)

    if exponent >= 0:
        decimals = 0
        whole_digits = digits_count + exponent
    else:
        decimals = -exponent
        whole_digits = digits_count - decimals
        if whole_digits < 0:
            whole_digits = 0

    if decimals > decimal_places:
        return False

    if whole_digits > (max_digits - decimal_places):
        return False

    return True


def _to_amount_for_field_or_none_on_overflow(value, field_name: str, path: str):
    if value in (None, ""):
        return None

    dec = _to_decimal(value, path)

    if not _decimal_fits_model_field(ProviderAssetContext, field_name, dec):
        return None

    return dec


def _to_amount_for_field_required(value, field_name: str, path: str) -> Decimal:
    dec = _to_decimal(value, path)

    if not _decimal_fits_model_field(ProviderAssetContext, field_name, dec):
        raise ValueError(
            f"{path}={value!r} does not fit ProviderAssetContext.{field_name}"
        )

    return dec


def _extract_exchange_info_index(payload) -> dict[str, list[dict]]:
    payload = _require_dict(payload, "exchange_info")

    if "symbols" not in payload:
        raise KeyError("Missing key: exchange_info.symbols")

    symbols = _require_list(payload["symbols"], "exchange_info.symbols")

    result: dict[str, list[dict]] = {}

    for idx, item in enumerate(symbols):
        item = _require_dict(item, f"exchange_info.symbols[{idx}]")

        for key in (
            "symbol",
            "baseAsset",
            "quoteAsset",
            "isSpotTradingAllowed",
            "baseAssetPrecision",
        ):
            if key not in item:
                raise KeyError(f"Missing key: exchange_info.symbols[{idx}].{key}")

        base_asset = str(item["baseAsset"]).strip().upper()
        if not base_asset:
            raise ValueError(f"exchange_info.symbols[{idx}].baseAsset is empty")

        result.setdefault(base_asset, []).append(item)

    return result


def _extract_capital_config_items(payload) -> list[dict]:
    payload = _require_list(payload, "capital_config_getall")

    result: list[dict] = []

    for idx, item in enumerate(payload):
        item = _require_dict(item, f"capital_config_getall[{idx}]")

        for key in ("coin", "name", "networkList"):
            if key not in item:
                raise KeyError(f"Missing key: capital_config_getall[{idx}].{key}")

        network_list = _require_list(
            item["networkList"],
            f"capital_config_getall[{idx}].networkList",
        )

        if not network_list:
            continue

        result.append(item)

    return result


def _build_trade_info(asset_code: str, exchange_info_items: list[dict]) -> dict:
    amount_precision = 8
    trades_enabled = False
    matched_symbols: list[dict] = []

    for idx, item in enumerate(exchange_info_items):
        path = f"exchange_info[{asset_code}][{idx}]"

        for key in ("baseAsset", "quoteAsset", "isSpotTradingAllowed", "baseAssetPrecision"):
            if key not in item:
                raise KeyError(f"Missing key: {path}.{key}")

        base_asset = str(item["baseAsset"]).strip().upper()
        if base_asset != asset_code:
            raise ValueError(f"{path}.baseAsset mismatch: {base_asset!r} != {asset_code!r}")

        quote_asset = str(item["quoteAsset"]).strip().upper()
        spot_allowed = _to_bool(item["isSpotTradingAllowed"], f"{path}.isSpotTradingAllowed")
        base_precision = _to_precision(item["baseAssetPrecision"], f"{path}.baseAssetPrecision", default=8)

        if base_precision > amount_precision:
            amount_precision = base_precision

        if spot_allowed:
            trades_enabled = True

        matched_symbols.append(
            {
                "symbol": str(item["symbol"]).strip(),
                "quoteAsset": quote_asset,
                "isSpotTradingAllowed": spot_allowed,
                "baseAssetPrecision": base_precision,
            }
        )

    return {
        "amount_precision": amount_precision,
        "trades_enabled": trades_enabled,
        "matched_symbols": matched_symbols,
    }


def sync_mexc_provider_asset_contexts_from_raw(provider: Provider) -> SyncCounters:
    capital_config_payload = _load_raw_json(provider.code, "capital_config_getall")
    exchange_info_payload = _load_raw_json(provider.code, "exchange_info")

    capital_items = _extract_capital_config_items(capital_config_payload)
    exchange_info_index = _extract_exchange_info_index(exchange_info_payload)
    stablecoin_codes = _get_stablecoin_codes()

    counters = SyncCounters()

    for asset_idx, asset_item in enumerate(capital_items):
        asset_path = f"capital_config_getall[{asset_idx}]"

        asset_code_pl = str(asset_item["coin"]).strip()
        asset_name_pl = str(asset_item["name"]).strip() or asset_code_pl

        if not asset_code_pl:
            raise ValueError(f"{asset_path}.coin is empty")

        asset_code = asset_code_pl.upper()

        if asset_code in exchange_info_index:
            trade_info = _build_trade_info(asset_code, exchange_info_index[asset_code])
        else:
            trade_info = {
                "amount_precision": 8,
                "trades_enabled": False,
                "matched_symbols": [],
            }

        network_list = _require_list(asset_item["networkList"], f"{asset_path}.networkList")

        for net_idx, network_item in enumerate(network_list):
            network_path = f"{asset_path}.networkList[{net_idx}]"
            network_item = _require_dict(network_item, network_path)

            for key in (
                "coin",
                "name",
                "network",
                "netWork",
                "depositEnable",
                "withdrawEnable",
                "minConfirm",
                "withdrawFee",
                "withdrawMax",
                "withdrawMin",
                "contract",
            ):
                if key not in network_item:
                    raise KeyError(f"Missing key: {network_path}.{key}")

            network_coin = str(network_item["coin"]).strip()
            if network_coin != asset_code_pl:
                raise ValueError(
                    f"{network_path}.coin mismatch: {network_coin!r} != {asset_code_pl!r}"
                )

            context_code_pl = str(network_item["netWork"]).strip()
            context_name_pl = str(network_item["network"]).strip()

            if not context_code_pl:
                raise ValueError(f"{network_path}.netWork is empty")
            if not context_name_pl:
                raise ValueError(f"{network_path}.network is empty")

            deposit_enable = _to_bool(network_item["depositEnable"], f"{network_path}.depositEnable")
            withdraw_enable = _to_bool(network_item["withdrawEnable"], f"{network_path}.withdrawEnable")
            min_confirm = _to_non_negative_int_zero(network_item["minConfirm"])

            withdraw_fee_fixed = _to_amount_for_field_required(
                network_item["withdrawFee"],
                "withdraw_fee_fixed",
                f"{network_path}.withdrawFee",
            )
            withdraw_min_amount = _to_amount_for_field_required(
                network_item["withdrawMin"],
                "withdraw_min_amount",
                f"{network_path}.withdrawMin",
            )
            withdraw_max_amount = _to_amount_for_field_or_none_on_overflow(
                network_item["withdrawMax"],
                "withdraw_max_amount",
                f"{network_path}.withdrawMax",
            )

            contract_raw = str(network_item["contract"]).strip()
            if contract_raw == "":
                contract_raw = None

            lookup = {
                "provider": provider,
                "asset_code": asset_code,
                "context_code": context_code_pl.upper(),
            }

            raw_metadata = {
                "capital_config_item": asset_item,
                "capital_network_item": network_item,
                "exchange_info_symbols": trade_info["matched_symbols"],
            }

            defaults = {
                "is_active": True,
                "asset_code_pl": asset_code_pl,
                "asset_name_pl": asset_name_pl,
                "context_code_pl": context_code_pl,
                "context_name_pl": context_name_pl,
                "asset_code": asset_code,
                "asset_name": asset_name_pl,
                "context_code": context_code_pl.upper(),
                "context_name": context_name_pl,
                "contract_raw": contract_raw,
                "raw_metadata": raw_metadata,
                "AD": deposit_enable,
                "AW": withdraw_enable,
                "deposit_confirmations": min_confirm,
                "withdraw_confirmations": 0,
                "deposit_fee_fixed": Decimal("0"),
                "deposit_fee_percent": Decimal("0"),
                "deposit_fee_min_amount": Decimal("0"),
                "deposit_fee_max_amount": None,
                "withdraw_fee_fixed": withdraw_fee_fixed,
                "withdraw_fee_percent": Decimal("0"),
                "withdraw_fee_min_amount": Decimal("0"),
                "withdraw_fee_max_amount": None,
                "deposit_min_amount": None,
                "deposit_max_amount": None,
                "withdraw_min_amount": withdraw_min_amount,
                "withdraw_max_amount": withdraw_max_amount,
                "is_stablecoin": asset_code in stablecoin_codes,
                "amount_precision": trade_info["amount_precision"],
                "nominal": 1,
                "trades_enabled": trade_info["trades_enabled"],
                "icon_url": "",
            }

            obj, created = ProviderAssetContext.objects.get_or_create(
                **lookup,
                defaults={
                    **defaults,
                    "match_status": ProviderAssetContextMatchStatus.NORMALIZED,
                },
            )

            if created:
                counters.created += 1
                continue

            changed = False

            update_fields = [
                "is_active",
                "asset_code_pl",
                "asset_name_pl",
                "context_code_pl",
                "context_name_pl",
                "asset_code",
                "asset_name",
                "context_code",
                "context_name",
                "contract_raw",
                "raw_metadata",
                "AD",
                "AW",
                "deposit_confirmations",
                "withdraw_confirmations",
                "deposit_fee_fixed",
                "deposit_fee_percent",
                "deposit_fee_min_amount",
                "deposit_fee_max_amount",
                "withdraw_fee_fixed",
                "withdraw_fee_percent",
                "withdraw_fee_min_amount",
                "withdraw_fee_max_amount",
                "deposit_min_amount",
                "deposit_max_amount",
                "withdraw_min_amount",
                "withdraw_max_amount",
                "is_stablecoin",
                "amount_precision",
                "nominal",
                "trades_enabled",
                "icon_url",
            ]

            for field_name in update_fields:
                new_value = defaults[field_name]
                old_value = getattr(obj, field_name)

                if old_value != new_value:
                    setattr(obj, field_name, new_value)
                    changed = True

            if changed:
                obj.save()
                counters.updated += 1
            else:
                counters.skipped += 1

    return counters