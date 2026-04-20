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


CONTEXT_ALIASES = {
    "BSC": "BEP20",
    "BSC20": "BEP20",
    "BEP20": "BEP20",
    "BNB": "BEP20",
    "TRX": "TRC20",
    "TRON": "TRC20",
    "TRC20": "TRC20",
    "POLYGON": "POLYGON",
    "MATIC": "POLYGON",
    "ERC20": "ERC20",
    "ARBITRUM": "ARBITRUM",
    "ARB": "ARBITRUM",
    "OPTIMISM": "OPTIMISM",
    "OP": "OPTIMISM",
    "BTC": "BTC",
    "LTC": "LTC",
    "TON": "TON",
    "ETC": "ETC",
    "SOL": "SOL",
}


def _load_raw_json(provider_code: str, request_type: str):
    path = get_raw_full_path(provider_code, request_type)
    if not path.exists():
        raise FileNotFoundError(
            f"Raw JSON не найден: storage/raw/{provider_code}/{request_type}.json"
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _require_dict(value, path: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be dict, got {type(value).__name__}")
    return value


def _require_list(value, path: str) -> list:
    if not isinstance(value, list):
        raise TypeError(f"{path} must be list, got {type(value).__name__}")
    return value


def _norm_text(value) -> str:
    return str(value or "").strip()


def _norm_code(value) -> str:
    return _norm_text(value).upper()


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value in (1, "1"):
        return True
    if value in (0, "0"):
        return False
    return False


def _to_non_negative_int_zero(value) -> int:
    if value in (None, ""):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
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
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_precision(value, default: int = 8) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
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


def _to_amount_for_field_or_none(value, field_name: str, path: str):
    dec = _to_decimal_or_none(value, path)
    if dec is None:
        return None
    if not _decimal_fits_model_field(ProviderAssetContext, field_name, dec):
        return None
    return dec


def _get_stablecoin_codes() -> set[str]:
    settings_obj = PlatformSettings.objects.first()
    if settings_obj:
        return set(settings_obj.get_stablecoin_codes())
    return set()


def _extract_token_items(payload) -> list[dict]:
    items = _require_list(payload, "token")
    result: list[dict] = []
    for idx, item in enumerate(items):
        item = _require_dict(item, f"token[{idx}]")
        for key in ("coinId", "chainId", "displayName", "rechargeable", "withdrawable"):
            if key not in item:
                raise KeyError(f"Missing key: token[{idx}].{key}")
        result.append(item)
    return result


def _extract_pairs_index(payload) -> dict[str, list[dict]]:
    items = _require_list(payload, "market_pairs")
    result: dict[str, list[dict]] = {}

    for idx, item in enumerate(items):
        item = _require_dict(item, f"market_pairs[{idx}]")
        asset_code = _norm_code(item.get("coinSymbol"))
        if not asset_code:
            continue
        result.setdefault(asset_code, []).append(item)

    return result


def _extract_processing_index(payload) -> dict[tuple[str, str], dict]:
    items = _require_list(payload, "available_token_settings")
    result: dict[tuple[str, str], dict] = {}

    for idx, item in enumerate(items):
        item = _require_dict(item, f"available_token_settings[{idx}]")
        coin = _norm_code(item.get("coin"))
        chain = item.get("chain")
        if not isinstance(chain, dict) or not coin:
            continue

        chain_name = _norm_code(chain.get("name"))
        chain_display_name = _norm_code(chain.get("displayName"))

        if chain_name:
            result[(coin, chain_name)] = item
        if chain_display_name:
            result[(coin, chain_display_name)] = item

    return result


def _normalize_context_code(
        *,
        asset_code: str,
        chain_id: str,
        display_name: str,
        contract_raw: str | None,
        processing_item: dict | None,
) -> tuple[str, str]:
    chain_name = ""
    chain_display_name = ""

    if isinstance(processing_item, dict):
        chain = processing_item.get("chain")
        if isinstance(chain, dict):
            chain_name = _norm_code(chain.get("name"))
            chain_display_name = _norm_code(chain.get("displayName"))

    # Приоритет: для токенов в контрактных сетях нормализуем в стандартизованный контекст
    candidates = [
        chain_display_name,
        chain_name,
        _norm_code(display_name),
        chain_id,
    ]

    if chain_id == "ETH":
        context_code = "ERC20" if contract_raw else "ETH"
    elif chain_id in ("TRX", "TRON"):
        context_code = "TRC20"
    elif chain_id in ("BSC", "BSC20", "BNB"):
        context_code = "BEP20"
    elif chain_id in ("POLYGON", "MATIC"):
        context_code = "POLYGON"
    else:
        context_code = ""
        for candidate in candidates:
            if not candidate:
                continue
            alias = CONTEXT_ALIASES.get(candidate)
            context_code = alias or candidate
            break

    if not context_code:
        context_code = chain_id or _norm_code(display_name)

    context_name = _norm_text(display_name)
    if not context_name and isinstance(processing_item, dict):
        chain = processing_item.get("chain")
        if isinstance(chain, dict):
            context_name = _norm_text(chain.get("displayName")) or _norm_text(chain.get("name"))
    if not context_name:
        context_name = context_code

    return context_code, context_name


def _build_trade_info(asset_code: str, pair_items: list[dict], fallback_precision: int = 8) -> dict:
    amount_precision = max(0, fallback_precision)
    trades_enabled = False
    matched_symbols: list[dict] = []
    min_trade_amount_usdt = None

    for idx, item in enumerate(pair_items):
        symbol = _norm_text(item.get("symbol"))
        coin_symbol = _norm_code(item.get("coinSymbol"))
        base_symbol = _norm_code(item.get("baseSymbol"))
        coin_scale = _to_precision(item.get("coinScale"), default=fallback_precision)
        exchangeable = _to_bool(item.get("exchangeable"))

        if coin_symbol and coin_symbol != asset_code:
            continue

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
                "fee": item.get("fee"),
            }
        )

        if exchangeable and base_symbol == "USDT":
            candidate = _to_amount_for_field_or_none(
                item.get("minTurnover"),
                "min_trade_amount_usdt",
                f"market_pairs[{asset_code}].minTurnover",
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

    try:
        processing_payload = _load_raw_json(provider.code, "available_token_settings")
    except FileNotFoundError:
        processing_payload = []

    token_items = _extract_token_items(token_payload)
    pairs_index = _extract_pairs_index(pairs_payload)
    processing_index = _extract_processing_index(processing_payload)
    stablecoin_codes = _get_stablecoin_codes()

    counters = SyncCounters()

    for asset_idx, token_item in enumerate(token_items):
        asset_path = f"token[{asset_idx}]"

        asset_code_pl = _norm_text(token_item.get("coinId"))
        context_code_pl = _norm_text(token_item.get("chainId"))
        context_name_pl = _norm_text(token_item.get("displayName")) or context_code_pl

        if not asset_code_pl:
            raise ValueError(f"{asset_path}.coinId is empty")
        if not context_code_pl:
            raise ValueError(f"{asset_path}.chainId is empty")

        asset_code = asset_code_pl.upper()

        processing_item = (
                processing_index.get((asset_code, _norm_code(context_code_pl)))
                or processing_index.get((asset_code, _norm_code(context_name_pl)))
        )

        processing_contract = None
        block_confirmations = 0
        if isinstance(processing_item, dict):
            processing_contract = processing_item.get("smartContractAddress")
            chain = processing_item.get("chain")
            if isinstance(chain, dict):
                block_confirmations = _to_non_negative_int_zero(chain.get("blockConfirmations"))

        contract_raw = _norm_text(
            token_item.get("smartContractAddress") or processing_contract or ""
        ) or None

        context_code, context_name = _normalize_context_code(
            asset_code=asset_code,
            chain_id=_norm_code(context_code_pl),
            display_name=context_name_pl,
            contract_raw=contract_raw,
            processing_item=processing_item,
        )

        asset_name_pl = asset_code_pl
        asset_name = asset_name_pl

        fallback_precision = _to_precision(token_item.get("scale"), default=8)
        trade_info = _build_trade_info(
            asset_code=asset_code,
            pair_items=pairs_index.get(asset_code, []),
            fallback_precision=fallback_precision,
        )

        deposit_is_working = _to_bool(token_item.get("rechargeable"))
        withdraw_is_working = _to_bool(token_item.get("withdrawable"))
        trades_enabled = trade_info["trades_enabled"]

        if not deposit_is_working and not withdraw_is_working and not trades_enabled:
            counters.skipped_inactive_assets += 1
            continue

        deposit_fee_fixed = _to_amount_for_field_or_none(
            token_item.get("rechargeFee"),
            "deposit_fee_fixed",
            f"{asset_path}.rechargeFee",
        )
        if deposit_fee_fixed is None:
            deposit_fee_fixed = Decimal("0")

        withdraw_fee_fixed = _to_amount_for_field_or_none(
            token_item.get("withdrawFee"),
            "withdraw_fee_fixed",
            f"{asset_path}.withdrawFee",
        )
        if withdraw_fee_fixed is None:
            withdraw_fee_fixed = Decimal("0")

        deposit_min_amount = _to_amount_for_field_or_none(
            token_item.get("minRecharge"),
            "deposit_min_amount",
            f"{asset_path}.minRecharge",
        )

        withdraw_min_amount = _to_amount_for_field_or_none(
            token_item.get("minWithdraw"),
            "withdraw_min_amount",
            f"{asset_path}.minWithdraw",
        )

        raw_metadata = {
            "token_item": token_item,
            "processing_item": processing_item,
            "pairs": trade_info["matched_symbols"],
        }

        lookup = {
            "provider": provider,
            "asset_code": asset_code,
            "context_code": context_code,
        }

        defaults = {
            "is_active": True,
            "asset_code_pl": asset_code_pl,
            "asset_name_pl": asset_name_pl,
            "context_code_pl": context_code_pl,
            "context_name_pl": context_name_pl,
            "contract_raw": contract_raw,
            "raw_metadata": raw_metadata,
            "asset_code": asset_code,
            "asset_name": asset_name,
            "context_code": context_code,
            "context_name": context_name,
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
            "min_trade_amount_usdt": trade_info["min_trade_amount_usdt"] or Decimal("5"),
            "trades_enabled": trades_enabled,
            "is_stablecoin": asset_code in stablecoin_codes,
            "amount_precision": trade_info["amount_precision"],
            "nominal": 1,
            "icon_url": "",
            "description": "",
        }

        obj, created = ProviderAssetContext.objects.get_or_create(
            **lookup,
            defaults={
                **defaults,
                "match_status": ProviderAssetContextMatchStatus.NORMALIZED,
                "D": True,
                "W": True,
            },
        )

        if created:
            counters.created += 1
            continue

        changed = False
        update_fields = [
            "is_active",
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
            "trades_enabled",
        ]

        for field_name in update_fields:
            new_value = defaults[field_name]
            old_value = getattr(obj, field_name)
            if old_value != new_value:
                setattr(obj, field_name, new_value)
                changed = True

        if obj.match_status == ProviderAssetContextMatchStatus.NEW:
            obj.match_status = ProviderAssetContextMatchStatus.NORMALIZED
            changed = True

        if changed:
            obj.save()
            counters.updated += 1
        else:
            counters.skipped += 1

    return counters
