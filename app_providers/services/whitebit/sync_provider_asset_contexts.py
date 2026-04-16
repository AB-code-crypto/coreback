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

WHITEBIT_UNLIMITED_MAX_SENTINEL = Decimal("999999999999999999")


def _to_fee_max_amount_or_none(value):
    if value in (None, ""):
        return None

    dec = _to_decimal(value)

    if dec == WHITEBIT_UNLIMITED_MAX_SENTINEL:
        return None

    return dec


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


def _normalize_set_from_list(value, path: str) -> set[str]:
    return {
        str(x).strip()
        for x in _require_list(value, path)
        if str(x).strip()
    }


def _read_source_sets(container: dict, path: str, *, require_any: bool) -> tuple[set[str], set[str]] | None:
    has_deposits = "deposits" in container
    has_withdraws = "withdraws" in container

    if require_any and not has_deposits and not has_withdraws:
        return None

    deposit_sources = set()
    withdraw_sources = set()

    if has_deposits:
        deposit_sources = _normalize_set_from_list(
            container["deposits"],
            f"{path}.deposits",
        )

    if has_withdraws:
        withdraw_sources = _normalize_set_from_list(
            container["withdraws"],
            f"{path}.withdraws",
        )

    return deposit_sources, withdraw_sources


def _first_non_empty(item: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def _to_int_zero(value) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_non_negative_int_zero(value) -> int:
    return max(0, _to_int_zero(value))


def _to_decimal(value, default: str = "0") -> Decimal:
    if value in (None, ""):
        value = default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _to_non_negative_decimal_or_none(value):
    if value in (None, ""):
        return None
    dec = _to_decimal(value)
    if dec < 0:
        return Decimal("0")
    return dec


def _to_precision(value, default: int = 8) -> int:
    if value in (None, ""):
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def _extract_maintenance_status(payload):
    payload = _require_dict(payload, "maintenance_status")
    if "status" not in payload:
        raise KeyError("Missing key: maintenance_status.status")
    return payload["status"]


def _maintenance_is_operational(status) -> bool:
    if status == 1:
        return True
    if status == 0:
        return False

    if isinstance(status, str):
        normalized = status.strip().lower()
        if normalized in {"system operational", "operational", "ok"}:
            return True
        if normalized in {"system maintenance", "maintenance"}:
            return False

    raise ValueError(f"Unknown maintenance status format: {status!r}")


def _extract_market_info_index(payload) -> dict[str, dict]:
    payload = _require_list(payload, "market_info")

    result: dict[str, dict] = {}

    for idx, item in enumerate(payload):
        item = _require_dict(item, f"market_info[{idx}]")

        if "type" not in item:
            raise KeyError(f"Missing key: market_info[{idx}].type")
        if "stock" not in item:
            raise KeyError(f"Missing key: market_info[{idx}].stock")
        if "money" not in item:
            raise KeyError(f"Missing key: market_info[{idx}].money")
        if "minTotal" not in item:
            raise KeyError(f"Missing key: market_info[{idx}].minTotal")
        if "tradesEnabled" not in item:
            raise KeyError(f"Missing key: market_info[{idx}].tradesEnabled")

        market_type = str(item["type"]).strip().lower()
        stock = str(item["stock"]).strip().upper()
        money = str(item["money"]).strip().upper()

        if not stock:
            raise ValueError(f"Empty stock in market_info[{idx}]")

        if market_type != "spot":
            continue

        if money != "USDT":
            continue

        result[stock] = item

    return result


def _extract_account_fee_index(payload) -> dict[str, dict]:
    payload = _require_list(payload, "account_fees")

    result: dict[str, dict] = {}

    for idx, item in enumerate(payload):
        item = _require_dict(item, f"account_fees[{idx}]")

        if "ticker" not in item:
            raise KeyError(f"Missing key: account_fees[{idx}].ticker")

        ticker = str(item["ticker"]).strip().upper()
        if not ticker:
            raise ValueError(f"Empty ticker in account_fees[{idx}]")

        result[ticker] = item

    return result


def _extract_contract(item: dict) -> str | None:
    value = _first_non_empty(
        item,
        (
            "contract",
            "contractAddress",
            "contract_address",
            "token_address",
            "address",
        ),
    )
    return str(value).strip() if value else None


def _extract_icon_url(item: dict) -> str:
    value = _first_non_empty(
        item,
        (
            "icon",
            "icon_url",
            "iconUrl",
            "logo",
            "logo_url",
            "logoUrl",
            "image",
            "image_url",
            "imageUrl",
        ),
    )
    return str(value).strip() if value else ""


def _extract_fee_block(account_fee_item: dict, direction: str, path: str) -> dict:
    if direction not in account_fee_item:
        raise KeyError(f"Missing key: {path}.{direction}")
    return _require_dict(account_fee_item[direction], f"{path}.{direction}")


def _classify_asset_status_item(item: dict, asset_code: str) -> str | None:
    has_confirmations = "confirmations" in item
    has_providers = "providers" in item

    if has_confirmations:
        return "crypto"

    if has_providers:
        return "fiat_currency"

    if "_" in asset_code:
        return "fiat_payment_method"

    # Бизнес-правило:
    # если не можем классифицировать и это не composite-code,
    # такую сущность пока пропускаем.
    return None


def _extract_confirmations_for_context(
        confirmations: dict,
        asset_code: str,
        context_code: str,
):
    if context_code not in confirmations:
        return 0, 0

    raw_value = confirmations[context_code]
    path = f"asset_status_list.{asset_code}.confirmations.{context_code}"

    if isinstance(raw_value, dict):
        deposit_value = _first_non_empty(
            raw_value,
            ("deposit", "in", "input", "value"),
        )
        if deposit_value is None:
            raise KeyError(f"Missing deposit-like key in {path}")

        withdraw_value = _first_non_empty(
            raw_value,
            ("withdraw", "out", "output", "value"),
        )
        if withdraw_value is None:
            raise KeyError(f"Missing withdraw-like key in {path}")

        return (
            _to_non_negative_int_zero(deposit_value),
            _to_non_negative_int_zero(withdraw_value),
        )

    value = _to_non_negative_int_zero(raw_value)
    return value, value


def _extract_limit_pair(
        limits_map: dict,
        asset_code: str,
        direction: str,
        context_code: str,
):
    if context_code not in limits_map:
        return None, None

    path = f"asset_status_list.{asset_code}.limits.{direction}.{context_code}"
    limit_item = _require_dict(limits_map[context_code], path)

    if "min" not in limit_item:
        raise KeyError(f"Missing key: {path}.min")

    min_amount = _to_non_negative_decimal_or_none(limit_item["min"])
    max_amount = _to_non_negative_decimal_or_none(limit_item.get("max"))

    return min_amount, max_amount


def _build_context_set(*parts) -> set[str]:
    result: set[str] = set()

    for part in parts:
        if isinstance(part, set):
            result |= {str(x).strip() for x in part if str(x).strip()}
        elif isinstance(part, dict):
            result |= {str(x).strip() for x in part.keys() if str(x).strip()}
        elif isinstance(part, str):
            value = part.strip()
            if value:
                result.add(value)

    return result


def _extract_asset_status_components(asset_code: str, item: dict):
    item = _require_dict(item, f"asset_status_list.{asset_code}")

    if "name" not in item:
        raise KeyError(f"Missing key: asset_status_list.{asset_code}.name")
    asset_name_pl = str(item["name"]).strip() or asset_code

    if "currency_precision" not in item:
        raise KeyError(f"Missing key: asset_status_list.{asset_code}.currency_precision")
    amount_precision = _to_precision(item["currency_precision"], default=8)

    if "limits" not in item:
        raise KeyError(f"Missing key: asset_status_list.{asset_code}.limits")
    limits = _require_dict(item["limits"], f"asset_status_list.{asset_code}.limits")

    if "deposit" not in limits:
        raise KeyError(f"Missing key: asset_status_list.{asset_code}.limits.deposit")
    if "withdraw" not in limits:
        raise KeyError(f"Missing key: asset_status_list.{asset_code}.limits.withdraw")

    deposit_limits = _require_dict(
        limits["deposit"],
        f"asset_status_list.{asset_code}.limits.deposit",
    )
    withdraw_limits = _require_dict(
        limits["withdraw"],
        f"asset_status_list.{asset_code}.limits.withdraw",
    )

    item_kind = _classify_asset_status_item(item, asset_code)
    if item_kind is None:
        return None

    if item_kind == "crypto":
        confirmations = _require_dict(
            item["confirmations"],
            f"asset_status_list.{asset_code}.confirmations",
        )

        if "networks" not in item:
            raise KeyError(f"Missing key: asset_status_list.{asset_code}.networks")

        networks = _require_dict(
            item["networks"],
            f"asset_status_list.{asset_code}.networks",
        )

        # Бизнес-правило:
        # если у crypto-актива нет deposits или withdraws keys,
        # значит актив сейчас нерабочий и мы его не импортируем.
        if "deposits" not in networks or "withdraws" not in networks:
            return None

        deposit_sources, withdraw_sources = _read_source_sets(
            networks,
            f"asset_status_list.{asset_code}.networks",
            require_any=False,
        )

        all_contexts = _build_context_set(
            deposit_sources,
            withdraw_sources,
            confirmations,
            deposit_limits,
            withdraw_limits,
        )

        return {
            "item_kind": "crypto",
            "item": item,
            "asset_code_pl": asset_code,
            "asset_name_pl": asset_name_pl,
            "amount_precision": amount_precision,
            "deposit_sources": deposit_sources,
            "withdraw_sources": withdraw_sources,
            "confirmations": confirmations,
            "deposit_limits": deposit_limits,
            "withdraw_limits": withdraw_limits,
            "all_contexts": all_contexts,
        }

    if item_kind == "fiat_currency":
        providers = _require_dict(
            item["providers"],
            f"asset_status_list.{asset_code}.providers",
        )

        # Бизнес-правило:
        # если у фиата нет providers.deposits или providers.withdraws,
        # значит мы пока не знаем, как его вводить/выводить, и пропускаем.
        if "deposits" not in providers or "withdraws" not in providers:
            return None

        deposit_sources, withdraw_sources = _read_source_sets(
            providers,
            f"asset_status_list.{asset_code}.providers",
            require_any=False,
        )

        all_contexts = _build_context_set(
            deposit_sources,
            withdraw_sources,
            deposit_limits,
            withdraw_limits,
        )

        return {
            "item_kind": "fiat_currency",
            "item": item,
            "asset_code_pl": asset_code,
            "asset_name_pl": asset_name_pl,
            "amount_precision": amount_precision,
            "deposit_sources": deposit_sources,
            "withdraw_sources": withdraw_sources,
            "confirmations": {},
            "deposit_limits": deposit_limits,
            "withdraw_limits": withdraw_limits,
            "all_contexts": all_contexts,
        }

    # fiat_payment_method
    if "networks" not in item:
        raise KeyError(f"Missing key: asset_status_list.{asset_code}.networks")

    networks = _require_dict(
        item["networks"],
        f"asset_status_list.{asset_code}.networks",
    )

    source_sets = _read_source_sets(
        networks,
        f"asset_status_list.{asset_code}.networks",
        require_any=True,
    )
    if source_sets is None:
        return None

    deposit_sources, withdraw_sources = source_sets
    base_asset_code, context_code = asset_code.split("_", 1)

    all_contexts = _build_context_set(
        deposit_sources,
        withdraw_sources,
        deposit_limits,
        withdraw_limits,
        context_code,
    )

    return {
        "item_kind": "fiat_payment_method",
        "item": item,
        "asset_code_pl": base_asset_code.strip(),
        "asset_name_pl": asset_name_pl,
        "amount_precision": amount_precision,
        "deposit_sources": deposit_sources,
        "withdraw_sources": withdraw_sources,
        "confirmations": {},
        "deposit_limits": deposit_limits,
        "withdraw_limits": withdraw_limits,
        "all_contexts": all_contexts,
        "raw_composite_code": asset_code,
    }


def _build_candidate_base(parsed: dict, context_code_pl: str) -> dict:
    return {
        "asset_code_pl": parsed["asset_code_pl"],
        "asset_name_pl": parsed["asset_name_pl"],
        "context_code_pl": context_code_pl,
        "context_name_pl": context_code_pl,
        "asset_code": parsed["asset_code_pl"].upper(),
        "asset_name": parsed["asset_name_pl"],
        "context_code": context_code_pl.upper(),
        "context_name": context_code_pl,
        "contract_raw": _extract_contract(parsed["item"]),
        "icon_url": _extract_icon_url(parsed["item"]),
        "amount_precision": parsed["amount_precision"],
        "item_kind": parsed["item_kind"],
        "raw_asset_item": parsed["item"],
    }


def _build_candidates(
        asset_status_payload: dict,
        account_fee_index: dict,
        market_info_index: dict,
):
    asset_status_payload = _require_dict(asset_status_payload, "asset_status_list")

    candidates: dict[tuple[str, str], dict] = {}
    skipped_inactive_assets = 0

    for raw_asset_code, raw_item in asset_status_payload.items():
        asset_code_raw = str(raw_asset_code).strip()
        if not asset_code_raw:
            raise ValueError("Empty asset code in asset_status_list")

        parsed = _extract_asset_status_components(asset_code_raw, raw_item)
        if parsed is None:
            skipped_inactive_assets += 1
            continue
        market_item = market_info_index.get(parsed["asset_code_pl"].upper())

        if market_item is None:
            trades_enabled = False
            min_trade_amount_usdt = Decimal("5")
        else:
            trades_enabled = bool(market_item["tradesEnabled"])
            min_trade_amount_usdt = _to_non_negative_decimal_or_none(market_item["minTotal"])
            if min_trade_amount_usdt is None:
                min_trade_amount_usdt = Decimal("5")
        account_fee_key = parsed.get("raw_composite_code", asset_code_raw).upper()
        account_fee_item = account_fee_index.get(account_fee_key)

        if account_fee_item is None and "raw_composite_code" in parsed:
            account_fee_item = account_fee_index.get(parsed["asset_code_pl"].upper())

        if account_fee_item is None:
            raise KeyError(f"account_fees entry not found for asset {account_fee_key}")

        deposit_fee_block = _extract_fee_block(
            account_fee_item,
            "deposit",
            f"account_fees[{account_fee_key}]",
        )
        withdraw_fee_block = _extract_fee_block(
            account_fee_item,
            "withdraw",
            f"account_fees[{account_fee_key}]",
        )

        for context_code_pl in sorted(parsed["all_contexts"]):
            deposit_confirmations, withdraw_confirmations = _extract_confirmations_for_context(
                parsed["confirmations"],
                asset_code_raw,
                context_code_pl,
            )

            deposit_min_amount, deposit_max_amount = _extract_limit_pair(
                parsed["deposit_limits"],
                asset_code_raw,
                "deposit",
                context_code_pl,
            )
            withdraw_min_amount, withdraw_max_amount = _extract_limit_pair(
                parsed["withdraw_limits"],
                asset_code_raw,
                "withdraw",
                context_code_pl,
            )

            has_deposit_source = context_code_pl in parsed["deposit_sources"]
            has_withdraw_source = context_code_pl in parsed["withdraw_sources"]
            has_deposit_limits = context_code_pl in parsed["deposit_limits"]
            has_withdraw_limits = context_code_pl in parsed["withdraw_limits"]

            if parsed["item_kind"] == "crypto":
                has_deposit_confirmations = context_code_pl in parsed["confirmations"]
                has_withdraw_confirmations = context_code_pl in parsed["confirmations"]

                ad = has_deposit_source and has_deposit_confirmations and has_deposit_limits
                aw = has_withdraw_source and has_withdraw_confirmations and has_withdraw_limits
            else:
                ad = has_deposit_source and has_deposit_limits
                aw = has_withdraw_source and has_withdraw_limits

            candidate = {
                **_build_candidate_base(parsed, context_code_pl),
                "AD": ad,
                "AW": aw,
                "deposit_confirmations": deposit_confirmations,
                "withdraw_confirmations": withdraw_confirmations,
                "deposit_min_amount": deposit_min_amount,
                "deposit_max_amount": deposit_max_amount,
                "withdraw_min_amount": withdraw_min_amount,
                "withdraw_max_amount": withdraw_max_amount,
                "deposit_fee_fixed": _to_decimal(deposit_fee_block.get("fixed"), default="0"),
                "deposit_fee_percent": _to_decimal(
                    deposit_fee_block["percentFlex"] if "percentFlex" in deposit_fee_block else deposit_fee_block.get("flex"),
                    default="0",
                ),
                "deposit_fee_min_amount": _to_decimal(deposit_fee_block.get("minFlex"), default="0"),
                "deposit_fee_max_amount": _to_fee_max_amount_or_none(deposit_fee_block.get("maxFlex")),
                "withdraw_fee_fixed": _to_decimal(withdraw_fee_block.get("fixed"), default="0"),
                "withdraw_fee_percent": _to_decimal(
                    withdraw_fee_block["percentFlex"] if "percentFlex" in withdraw_fee_block else withdraw_fee_block.get("flex"),
                    default="0",
                ),
                "withdraw_fee_min_amount": _to_decimal(withdraw_fee_block.get("minFlex"), default="0"),
                "withdraw_fee_max_amount": _to_fee_max_amount_or_none(withdraw_fee_block.get("maxFlex")),
                "raw_fee_item": account_fee_item,
                "trades_enabled": trades_enabled,
                "min_trade_amount_usdt": min_trade_amount_usdt,
                "raw_market_item": market_item or {},
            }

            key = (candidate["asset_code"], candidate["context_code"])
            candidates[key] = candidate

    return candidates, skipped_inactive_assets


def sync_whitebit_provider_asset_contexts_from_raw(provider: Provider) -> SyncCounters:
    asset_status_payload = _load_raw_json(provider.code, "asset_status_list")
    account_fees_payload = _load_raw_json(provider.code, "account_fees")
    market_info_payload = _load_raw_json(provider.code, "market_info")
    maintenance_payload = _load_raw_json(provider.code, "maintenance_status")

    maintenance_status = _extract_maintenance_status(maintenance_payload)
    is_operational = _maintenance_is_operational(maintenance_status)

    account_fee_index = _extract_account_fee_index(account_fees_payload)
    market_info_index = _extract_market_info_index(market_info_payload)

    candidates, skipped_inactive_assets = _build_candidates(
        asset_status_payload,
        account_fee_index,
        market_info_index,
    )
    stablecoin_codes = _get_stablecoin_codes()

    counters = SyncCounters(skipped_inactive_assets=skipped_inactive_assets)

    for candidate in candidates.values():
        ad = bool(candidate["AD"])
        aw = bool(candidate["AW"])

        if not is_operational:
            ad = False
            aw = False

        raw_metadata = {
            "item_kind": candidate["item_kind"],
            "asset_status_item": candidate["raw_asset_item"],
            "account_fee_item": candidate["raw_fee_item"],
            "market_info_item": candidate["raw_market_item"],
            "maintenance_status": maintenance_status,
        }

        lookup = {
            "provider": provider,
            "asset_code": candidate["asset_code"],
            "context_code": candidate["context_code"],
        }

        defaults = {
            "is_active": True,
            "asset_code_pl": candidate["asset_code_pl"],
            "asset_name_pl": candidate["asset_name_pl"],
            "context_code_pl": candidate["context_code_pl"],
            "context_name_pl": candidate["context_name_pl"],
            "asset_name": candidate["asset_name"],
            "context_name": candidate["context_name"],
            "contract_raw": candidate["contract_raw"],
            "raw_metadata": raw_metadata,
            "AD": ad,
            "AW": aw,
            "deposit_confirmations": _to_non_negative_int_zero(candidate["deposit_confirmations"]),
            "withdraw_confirmations": _to_non_negative_int_zero(candidate["withdraw_confirmations"]),
            "deposit_fee_fixed": candidate["deposit_fee_fixed"],
            "deposit_fee_percent": candidate["deposit_fee_percent"],
            "deposit_fee_min_amount": candidate["deposit_fee_min_amount"],
            "deposit_fee_max_amount": candidate["deposit_fee_max_amount"],
            "withdraw_fee_fixed": candidate["withdraw_fee_fixed"],
            "withdraw_fee_percent": candidate["withdraw_fee_percent"],
            "withdraw_fee_min_amount": candidate["withdraw_fee_min_amount"],
            "withdraw_fee_max_amount": candidate["withdraw_fee_max_amount"],
            "deposit_min_amount": candidate["deposit_min_amount"],
            "deposit_max_amount": candidate["deposit_max_amount"],
            "withdraw_min_amount": candidate["withdraw_min_amount"],
            "withdraw_max_amount": candidate["withdraw_max_amount"],
            "is_stablecoin": candidate["asset_code"] in stablecoin_codes,
            "amount_precision": _to_precision(candidate["amount_precision"], default=8),
            "nominal": 1,
            "trades_enabled": candidate["trades_enabled"],
            "min_trade_amount_usdt": candidate["min_trade_amount_usdt"],
            "icon_url": candidate["icon_url"],
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
            "asset_name",
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
            "min_trade_amount_usdt",
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
