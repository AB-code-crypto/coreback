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


def _to_bool(value, path: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in (1, "1"):
        return True
    if value in (0, "0"):
        return False
    raise TypeError(f"{path} must be bool-like, got {value!r}")


def _to_decimal(value, path: str) -> Decimal:
    if value in (None, ""):
        raise ValueError(f"{path} is empty")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be decimal-compatible, got {value!r}") from exc


def _to_precision(value, path: str, default: int = 8) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{path} must be int-compatible, got {value!r}")
    return max(0, parsed)


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


def _extract_token_items(payload) -> list[dict]:
    items = _require_list(payload, "token")
    result: list[dict] = []
    for idx, item in enumerate(items):
        item = _require_dict(item, f"token[{idx}]")
        for key in ("coinId", "chainId", "displayName", "rechargeable", "withdrawable", "scale"):
            if key not in item:
                raise KeyError(f"Missing key: token[{idx}].{key}")
        result.append(item)
    return result


def _extract_pairs_index(payload) -> dict[str, list[dict]]:
    items = _require_list(payload, "market_pairs")
    result: dict[str, list[dict]] = {}

    for idx, item in enumerate(items):
        item = _require_dict(item, f"market_pairs[{idx}]")
        for key in ("symbol", "coinSymbol", "baseSymbol", "coinScale", "exchangeable"):
            if key not in item:
                raise KeyError(f"Missing key: market_pairs[{idx}].{key}")

        asset_code = str(item["coinSymbol"]).strip().upper()
        if not asset_code:
            raise ValueError(f"market_pairs[{idx}].coinSymbol is empty")

        result.setdefault(asset_code, []).append(item)

    return result


def _extract_balance_name_index(payload) -> dict[str, str]:
    items = _require_list(payload, "balances")
    result: dict[str, str] = {}

    for idx, item in enumerate(items):
        item = _require_dict(item, f"balances[{idx}]")
        unit = str(item.get("unit") or "").strip().upper()
        name = str(item.get("name") or "").strip()
        if unit and name:
            result[unit] = name

    return result


def _extract_processing_index(payload) -> dict[tuple[str, str], dict]:
    items = _require_list(payload, "available_token_settings")
    result: dict[tuple[str, str], dict] = {}

    for idx, item in enumerate(items):
        item = _require_dict(item, f"available_token_settings[{idx}]")
        coin = str(item.get("coin") or "").strip().upper()
        chain = item.get("chain")
        if not isinstance(chain, dict):
            continue

        chain_name = str(chain.get("name") or "").strip().upper()
        chain_display_name = str(chain.get("displayName") or "").strip().upper()

        if coin and chain_name:
            result[(coin, chain_name)] = item
        if coin and chain_display_name:
            result[(coin, chain_display_name)] = item

    return result


def _build_trade_info(asset_code: str, pair_items: list[dict], fallback_precision: int = 8) -> dict:
    amount_precision = max(0, fallback_precision)
    trades_enabled = False
    matched_symbols: list[dict] = []
    min_trade_amount_usdt = None

    for idx, item in enumerate(pair_items):
        path = f"market_pairs[{asset_code}][{idx}]"

        symbol = str(item.get("symbol") or "").strip().upper()
        coin_symbol = str(item.get("coinSymbol") or "").strip().upper()
        base_symbol = str(item.get("baseSymbol") or "").strip().upper()
        coin_scale = _to_precision(item.get("coinScale"), f"{path}.coinScale", default=fallback_precision)
        exchangeable = _to_bool(item.get("exchangeable"), f"{path}.exchangeable")

        if coin_symbol != asset_code:
            raise ValueError(f"{path}.coinSymbol mismatch: {coin_symbol!r} != {asset_code!r}")

        amount_precision = max(amount_precision, coin_scale)
        if exchangeable:
            trades_enabled = True

        matched_symbols.append(
            {
                "symbol": symbol,
                "baseSymbol": base_symbol,
                "coinScale": coin_scale,
                "exchangeable": exchangeable,
                "minTurnover": item.get("minTurnover"),
                "minVolume": item.get("minVolume"),
            }
        )

        if exchangeable and base_symbol == "USDT":
            candidate = _to_amount_for_field_or_none_on_overflow(
                item.get("minTurnover"),
                "min_trade_amount_usdt",
                f"{path}.minTurnover",
            )
            if candidate is not None and candidate > 0:
                if min_trade_amount_usdt is None or candidate < min_trade_amount_usdt:
                    min_trade_amount_usdt = candidate

    return {
        "amount_precision": amount_precision,
        "trades_enabled": trades_enabled,
        "matched_symbols": matched_symbols,
        "min_trade_amount_usdt": min_trade_amount_usdt,
    }


def sync_rapira_provider_asset_contexts_from_raw(provider: Provider) -> SyncCounters:
    token_payload = _load_raw_json(provider.code, "token")
    pairs_payload = _load_raw_json(provider.code, "market_pairs")
    balances_payload = _load_raw_json(provider.code, "balances")

    try:
        processing_payload = _load_raw_json(provider.code, "available_token_settings")
    except FileNotFoundError:
        processing_payload = []

    token_items = _extract_token_items(token_payload)
    pairs_index = _extract_pairs_index(pairs_payload)
    balance_name_index = _extract_balance_name_index(balances_payload)
    processing_index = _extract_processing_index(processing_payload)
    stablecoin_codes = _get_stablecoin_codes()

    counters = SyncCounters()

    for asset_idx, token_item in enumerate(token_items):
        asset_path = f"token[{asset_idx}]"

        asset_code_pl = str(token_item["coinId"]).strip()
        context_code_pl = str(token_item["chainId"]).strip()
        context_name_pl = str(token_item["displayName"]).strip() or context_code_pl

        if not asset_code_pl:
            raise ValueError(f"{asset_path}.coinId is empty")
        if not context_code_pl:
            raise ValueError(f"{asset_path}.chainId is empty")

        asset_code = asset_code_pl.upper()
        context_code = context_code_pl.upper()

        asset_name_pl = balance_name_index.get(asset_code, asset_code_pl)
        asset_name = asset_name_pl

        fallback_precision = _to_precision(token_item.get("scale"), f"{asset_path}.scale", default=8)
        trade_info = _build_trade_info(
            asset_code=asset_code,
            pair_items=pairs_index.get(asset_code, []),
            fallback_precision=fallback_precision,
        )

        processing_item = (
            processing_index.get((asset_code, context_name_pl.upper()))
            or processing_index.get((asset_code, context_code))
        )

        block_confirmations = 0
        processing_contract = None
        if isinstance(processing_item, dict):
            chain = processing_item.get("chain")
            if isinstance(chain, dict):
                block_confirmations = _to_non_negative_int_zero(chain.get("blockConfirmations"))
            processing_contract = processing_item.get("smartContractAddress")

        deposit_is_working = _to_bool(token_item.get("rechargeable"), f"{asset_path}.rechargeable")
        withdraw_is_working = _to_bool(token_item.get("withdrawable"), f"{asset_path}.withdrawable")

        if not deposit_is_working and not withdraw_is_working and not trade_info["trades_enabled"]:
            counters.skipped_inactive_assets += 1
            continue

        deposit_fee_fixed = _to_amount_for_field_or_none_on_overflow(
            token_item.get("rechargeFee"),
            "deposit_fee_fixed",
            f"{asset_path}.rechargeFee",
        )
        if deposit_fee_fixed is None:
            deposit_fee_fixed = Decimal("0")

        withdraw_fee_fixed = _to_amount_for_field_or_none_on_overflow(
            token_item.get("withdrawFee"),
            "withdraw_fee_fixed",
            f"{asset_path}.withdrawFee",
        )
        if withdraw_fee_fixed is None:
            withdraw_fee_fixed = Decimal("0")

        deposit_min_amount = _to_amount_for_field_or_none_on_overflow(
            token_item.get("minRecharge"),
            "deposit_min_amount",
            f"{asset_path}.minRecharge",
        )
        if deposit_min_amount is None:
            deposit_min_amount = Decimal("0")

        withdraw_min_amount = _to_amount_for_field_or_none_on_overflow(
            token_item.get("minWithdraw"),
            "withdraw_min_amount",
            f"{asset_path}.minWithdraw",
        )

        contract_raw = str(
            token_item.get("smartContractAddress")
            or processing_contract
            or ""
        ).strip() or None

        lookup = {
            "provider": provider,
            "asset_code": asset_code,
            "context_code": context_code,
        }

        raw_metadata = {
            "token_item": token_item,
            "trade_info": trade_info["matched_symbols"],
            "processing_item": processing_item,
        }

        defaults = {
            "is_active": True,
            "asset_code_pl": asset_code_pl,
            "asset_name_pl": asset_name_pl,
            "context_code_pl": context_code_pl,
            "context_name_pl": context_name_pl,
            "asset_code": asset_code,
            "asset_name": asset_name,
            "context_code": context_code,
            "context_name": context_name_pl,
            "contract_raw": contract_raw,
            "raw_metadata": raw_metadata,
            "AD": deposit_is_working,
            "AW": withdraw_is_working,
            "deposit_confirmations": block_confirmations if deposit_is_working else 0,
            "withdraw_confirmations": block_confirmations if withdraw_is_working else 0,
            "deposit_fee_fixed": deposit_fee_fixed,
            "deposit_fee_percent": Decimal("0"),
            "deposit_fee_min_amount": Decimal("0"),
            "deposit_fee_max_amount": None,
            "withdraw_fee_fixed": withdraw_fee_fixed,
            "withdraw_fee_percent": Decimal("0"),
            "withdraw_fee_min_amount": Decimal("0"),
            "withdraw_fee_max_amount": None,
            "deposit_min_amount": deposit_min_amount,
            "deposit_max_amount": None,
            "withdraw_min_amount": withdraw_min_amount,
            "withdraw_max_amount": None,
            "min_trade_amount_usdt": trade_info["min_trade_amount_usdt"],
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
            "min_trade_amount_usdt",
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