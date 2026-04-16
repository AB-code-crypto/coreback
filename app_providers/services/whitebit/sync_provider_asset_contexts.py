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
    for key in (
            "contract",
            "contractAddress",
            "contract_address",
            "token_address",
            "address",
    ):
        if key in item and item[key]:
            return str(item[key]).strip()
    return None


def _extract_icon_url(item: dict) -> str:
    for key in (
            "icon",
            "icon_url",
            "iconUrl",
            "logo",
            "logo_url",
            "logoUrl",
            "image",
            "image_url",
            "imageUrl",
    ):
        if key in item and item[key]:
            return str(item[key]).strip()
    return ""


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
    # значит пока не работаем с такой сущностью и пропускаем её.
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
        if "deposit" in raw_value:
            deposit_value = raw_value["deposit"]
        elif "in" in raw_value:
            deposit_value = raw_value["in"]
        elif "input" in raw_value:
            deposit_value = raw_value["input"]
        elif "value" in raw_value:
            deposit_value = raw_value["value"]
        else:
            raise KeyError(f"Missing deposit-like key in {path}")

        if "withdraw" in raw_value:
            withdraw_value = raw_value["withdraw"]
        elif "out" in raw_value:
            withdraw_value = raw_value["out"]
        elif "output" in raw_value:
            withdraw_value = raw_value["output"]
        elif "value" in raw_value:
            withdraw_value = raw_value["value"]
        else:
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
        # если у crypto-актива вообще нет deposits/withdraws keys,
        # значит актив сейчас нерабочий и мы его не импортируем.
        if "deposits" not in networks or "withdraws" not in networks:
            return None

        deposit_sources = {
            str(x).strip()
            for x in _require_list(
                networks["deposits"],
                f"asset_status_list.{asset_code}.networks.deposits",
            )
            if str(x).strip()
        }
        withdraw_sources = {
            str(x).strip()
            for x in _require_list(
                networks["withdraws"],
                f"asset_status_list.{asset_code}.networks.withdraws",
            )
            if str(x).strip()
        }

        all_contexts = (
                set(deposit_sources)
                | set(withdraw_sources)
                | {str(x).strip() for x in confirmations.keys() if str(x).strip()}
                | {str(x).strip() for x in deposit_limits.keys() if str(x).strip()}
                | {str(x).strip() for x in withdraw_limits.keys() if str(x).strip()}
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
        # значит мы пока не знаем, как его вводить/выводить,
        # и такую валюту не импортируем.
        if "deposits" not in providers or "withdraws" not in providers:
            return None

        deposit_sources = {
            str(x).strip()
            for x in _require_list(
                providers["deposits"],
                f"asset_status_list.{asset_code}.providers.deposits",
            )
            if str(x).strip()
        }
        withdraw_sources = {
            str(x).strip()
            for x in _require_list(
                providers["withdraws"],
                f"asset_status_list.{asset_code}.providers.withdraws",
            )
            if str(x).strip()
        }

        all_contexts = (
                set(deposit_sources)
                | set(withdraw_sources)
                | {str(x).strip() for x in deposit_limits.keys() if str(x).strip()}
                | {str(x).strip() for x in withdraw_limits.keys() if str(x).strip()}
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
    # fiat_payment_method
    if "networks" not in item:
        raise KeyError(f"Missing key: asset_status_list.{asset_code}.networks")

    networks = _require_dict(
        item["networks"],
        f"asset_status_list.{asset_code}.networks",
    )

    has_deposits_key = "deposits" in networks
    has_withdraws_key = "withdraws" in networks

    # Бизнес-правило:
    # если нет ни deposits, ни withdraws, то такой платёжный метод пока нерабочий
    # и мы его не импортируем.
    if not has_deposits_key and not has_withdraws_key:
        return None

    deposit_sources = set()
    withdraw_sources = set()

    if has_deposits_key:
        deposit_sources = {
            str(x).strip()
            for x in _require_list(
                networks["deposits"],
                f"asset_status_list.{asset_code}.networks.deposits",
            )
            if str(x).strip()
        }

    if has_withdraws_key:
        withdraw_sources = {
            str(x).strip()
            for x in _require_list(
                networks["withdraws"],
                f"asset_status_list.{asset_code}.networks.withdraws",
            )
            if str(x).strip()
        }

    base_asset_code, context_code = asset_code.split("_", 1)

    all_contexts = (
            set(deposit_sources)
            | set(withdraw_sources)
            | {str(x).strip() for x in deposit_limits.keys() if str(x).strip()}
            | {str(x).strip() for x in withdraw_limits.keys() if str(x).strip()}
            | {context_code.strip()}
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


def _build_candidates(asset_status_payload: dict, account_fee_index: dict):
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

        account_fee_key = (
            parsed.get("raw_composite_code", asset_code_raw).upper()
        )
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

            key = (parsed["asset_code_pl"].upper(), context_code_pl.upper())

            candidates[key] = {
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
                "deposit_fee_max_amount": _to_decimal(deposit_fee_block.get("maxFlex"), default="0"),
                "withdraw_fee_fixed": _to_decimal(withdraw_fee_block.get("fixed"), default="0"),
                "withdraw_fee_percent": _to_decimal(
                    withdraw_fee_block["percentFlex"] if "percentFlex" in withdraw_fee_block else withdraw_fee_block.get("flex"),
                    default="0",
                ),
                "withdraw_fee_min_amount": _to_decimal(withdraw_fee_block.get("minFlex"), default="0"),
                "withdraw_fee_max_amount": _to_decimal(withdraw_fee_block.get("maxFlex"), default="0"),
                "item_kind": parsed["item_kind"],
                "raw_asset_item": parsed["item"],
                "raw_fee_item": account_fee_item,
            }

    return candidates, skipped_inactive_assets


def sync_whitebit_provider_asset_contexts_from_raw(provider: Provider) -> SyncCounters:
    asset_status_payload = _load_raw_json(provider.code, "asset_status_list")
    account_fees_payload = _load_raw_json(provider.code, "account_fees")
    maintenance_payload = _load_raw_json(provider.code, "maintenance_status")

    maintenance_status = _extract_maintenance_status(maintenance_payload)
    is_operational = _maintenance_is_operational(maintenance_status)

    account_fee_index = _extract_account_fee_index(account_fees_payload)
    candidates, skipped_inactive_assets = _build_candidates(
        asset_status_payload,
        account_fee_index,
    )
    stablecoin_codes = _get_stablecoin_codes()

    counters = SyncCounters(skipped_inactive_assets=skipped_inactive_assets)

    for candidate in candidates.values():
        ad = bool(candidate["AD"])
        aw = bool(candidate["AW"])

        if not is_operational:
            ad = False
            aw = False
            status_note = "Platform maintenance"
        else:
            status_note = ""

        raw_metadata = {
            "item_kind": candidate["item_kind"],
            "asset_status_item": candidate["raw_asset_item"],
            "account_fee_item": candidate["raw_fee_item"],
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
            "status_note": status_note,
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
            "status_note",
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
