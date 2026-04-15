import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app_core.models import PlatformSettings
from app_providers.models.provider import Provider, ProviderCode
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


def _to_non_negative_int_zero(value) -> int:
    if value in (None, ""):
        return 0
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _to_decimal(value, default: str = "0") -> Decimal:
    if value in (None, ""):
        value = default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _to_non_negative_decimal(value, default: str = "0") -> Decimal:
    dec = _to_decimal(value, default=default)
    if dec < 0:
        return Decimal("0")
    return dec


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
    if not isinstance(payload, dict):
        return None
    return payload.get("status")


def _maintenance_is_operational(status) -> bool | None:
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

    return None


def _extract_account_fee_index(payload) -> dict[str, dict]:
    result = {}

    if not isinstance(payload, list):
        return result

    for item in payload:
        if not isinstance(item, dict):
            continue

        ticker = str(item.get("ticker") or "").strip().upper()
        if not ticker:
            continue

        result[ticker] = item

    return result


def _get_operational_networks(item: dict) -> tuple[set[str], set[str]]:
    networks = item.get("networks") or {}

    deposits = set(networks.get("deposits") or [])
    withdraws = set(networks.get("withdraws") or [])

    return deposits, withdraws


def _get_provider_contexts(item: dict) -> tuple[set[str], set[str]]:
    providers = item.get("providers") or {}

    deposits = set(providers.get("deposits") or [])
    withdraws = set(providers.get("withdraws") or [])

    return deposits, withdraws


def _is_composite_code(code: str, all_codes: set[str]) -> bool:
    if "_" not in code:
        return False
    base_code = code.split("_", 1)[0]
    return base_code in all_codes


def _extract_confirmations(item: dict, context_code: str) -> tuple[int, int]:
    confirmations = item.get("confirmations") or {}
    raw_value = confirmations.get(context_code)

    if raw_value is None:
        return 0, 0

    if isinstance(raw_value, dict):
        deposit_value = (
                raw_value.get("deposit")
                or raw_value.get("in")
                or raw_value.get("input")
                or raw_value.get("value")
        )
        withdraw_value = (
                raw_value.get("withdraw")
                or raw_value.get("out")
                or raw_value.get("output")
                or raw_value.get("value")
        )
        return (
            _to_non_negative_int_zero(deposit_value),
            _to_non_negative_int_zero(withdraw_value),
        )

    value = _to_non_negative_int_zero(raw_value)
    return value, value


def _extract_amount_limits(item: dict, context_code: str, direction: str):
    limits = item.get("limits") or {}
    direction_limits = (limits.get(direction) or {}).get(context_code) or {}

    if not isinstance(direction_limits, dict):
        return None, None

    min_amount = direction_limits.get("min") or direction_limits.get("min_amount")
    max_amount = direction_limits.get("max") or direction_limits.get("max_amount")

    return (
        _to_non_negative_decimal_or_none(min_amount),
        _to_non_negative_decimal_or_none(max_amount),
    )


def _extract_contract(item: dict):
    for key in (
            "contract",
            "contractAddress",
            "contract_address",
            "token_address",
            "address",
    ):
        value = item.get(key)
        if value:
            return str(value).strip()
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
        value = item.get(key)
        if value:
            return str(value).strip()
    return ""


def _extract_amount_precision(item: dict) -> int:
    for key in (
            "precision",
            "amount_precision",
            "display_precision",
            "decimals",
    ):
        if key in item and item.get(key) not in (None, ""):
            return _to_precision(item.get(key), default=8)
    return 8


def _build_candidates(asset_status_payload: dict, account_fee_index: dict) -> dict[tuple[str, str], dict]:
    if not isinstance(asset_status_payload, dict):
        raise ValueError("asset_status_list.json должен быть JSON object.")

    all_codes = set(asset_status_payload.keys())

    candidates: dict[tuple[str, str], dict] = {}
    composite_overrides: list[tuple[str, dict]] = []

    for raw_code, item in asset_status_payload.items():
        if not isinstance(item, dict):
            continue

        if _is_composite_code(raw_code, all_codes):
            composite_overrides.append((raw_code, item))
            continue

        asset_code_pl = str(raw_code).strip()
        asset_name_pl = str(item.get("name") or asset_code_pl).strip()

        deposit_networks, withdraw_networks = _get_operational_networks(item)
        provider_deposits, provider_withdraws = _get_provider_contexts(item)

        operational_contexts = deposit_networks | withdraw_networks
        provider_contexts = provider_deposits | provider_withdraws

        if provider_contexts:
            contexts = provider_contexts
            deposit_context_set = provider_deposits
            withdraw_context_set = provider_withdraws
        else:
            contexts = operational_contexts
            deposit_context_set = deposit_networks
            withdraw_context_set = withdraw_networks

        for context_code_raw in sorted(contexts):
            context_code_pl = str(context_code_raw).strip()
            if not context_code_pl:
                continue

            deposit_confirmations, withdraw_confirmations = _extract_confirmations(
                item,
                context_code_pl,
            )
            deposit_min_amount, deposit_max_amount = _extract_amount_limits(
                item,
                context_code_pl,
                "deposit",
            )
            withdraw_min_amount, withdraw_max_amount = _extract_amount_limits(
                item,
                context_code_pl,
                "withdraw",
            )

            key = (asset_code_pl.upper(), context_code_pl.upper())

            candidates[key] = {
                "asset_code_pl": asset_code_pl,
                "asset_name_pl": asset_name_pl,
                "context_code_pl": context_code_pl,
                "context_name_pl": context_code_pl,
                "asset_code": asset_code_pl.upper(),
                "context_code": context_code_pl.upper(),
                "asset_name": asset_name_pl,
                "context_name": context_code_pl,
                "contract_raw": _extract_contract(item),
                "icon_url": _extract_icon_url(item),
                "amount_precision": _extract_amount_precision(item),
                "AD": context_code_pl in deposit_context_set,
                "AW": context_code_pl in withdraw_context_set,
                "deposit_confirmations": deposit_confirmations,
                "withdraw_confirmations": withdraw_confirmations,
                "deposit_min_amount": deposit_min_amount,
                "deposit_max_amount": deposit_max_amount,
                "withdraw_min_amount": withdraw_min_amount,
                "withdraw_max_amount": withdraw_max_amount,
                "provider_entity_code": asset_code_pl,
                "raw_asset_item": item,
            }

    # Накладываем composite-коды поверх уже собранных кандидатов
    for composite_code, item in composite_overrides:
        base_code, context_guess = composite_code.split("_", 1)

        key = (base_code.upper(), context_guess.upper())
        existing = candidates.get(key)

        if existing is None:
            existing = {
                "asset_code_pl": base_code,
                "asset_name_pl": str(item.get("name") or base_code).strip(),
                "context_code_pl": context_guess,
                "context_name_pl": context_guess,
                "asset_code": base_code.upper(),
                "context_code": context_guess.upper(),
                "asset_name": str(item.get("name") or base_code).strip(),
                "context_name": context_guess,
                "contract_raw": _extract_contract(item),
                "icon_url": _extract_icon_url(item),
                "amount_precision": _extract_amount_precision(item),
                "AD": False,
                "AW": False,
                "deposit_confirmations": 0,
                "withdraw_confirmations": 0,
                "deposit_min_amount": None,
                "deposit_max_amount": None,
                "withdraw_min_amount": None,
                "withdraw_max_amount": None,
                "provider_entity_code": composite_code,
                "raw_asset_item": item,
            }
            candidates[key] = existing

        existing["provider_entity_code"] = composite_code
        existing["raw_asset_item"] = item
        existing["AD"] = bool(item.get("can_deposit", existing["AD"]))
        existing["AW"] = bool(item.get("can_withdraw", existing["AW"]))

        contract_raw = _extract_contract(item)
        if contract_raw:
            existing["contract_raw"] = contract_raw

        icon_url = _extract_icon_url(item)
        if icon_url:
            existing["icon_url"] = icon_url

    # Накладываем private account fees
    for candidate in candidates.values():
        fee_item = (
                account_fee_index.get(str(candidate["provider_entity_code"]).upper())
                or account_fee_index.get(str(candidate["asset_code_pl"]).upper())
        )

        deposit = (fee_item or {}).get("deposit") or {}
        withdraw = (fee_item or {}).get("withdraw") or {}

        if fee_item:
            candidate["AD"] = candidate["AD"] and bool(fee_item.get("can_deposit", True))
            candidate["AW"] = candidate["AW"] and bool(fee_item.get("can_withdraw", True))

        candidate["deposit_fee_fixed"] = _to_decimal(deposit.get("fixed"), default="0")
        candidate["deposit_fee_percent"] = _to_decimal(deposit.get("percentFlex") or deposit.get("flex"), default="0")
        candidate["deposit_fee_min_amount"] = _to_decimal(deposit.get("minFlex"), default="0")
        candidate["deposit_fee_max_amount"] = _to_decimal(deposit.get("maxFlex"), default="0")

        candidate["withdraw_fee_fixed"] = _to_decimal(withdraw.get("fixed"), default="0")
        candidate["withdraw_fee_percent"] = _to_decimal(withdraw.get("percentFlex") or withdraw.get("flex"), default="0")
        candidate["withdraw_fee_min_amount"] = _to_decimal(withdraw.get("minFlex"), default="0")
        candidate["withdraw_fee_max_amount"] = _to_decimal(withdraw.get("maxFlex"), default="0")

        candidate["deposit_min_amount"] = _to_non_negative_decimal_or_none(
            deposit.get("minAmount")
        ) or candidate.get("deposit_min_amount")
        candidate["deposit_max_amount"] = _to_non_negative_decimal_or_none(
            deposit.get("maxAmount")
        ) or candidate.get("deposit_max_amount")
        candidate["withdraw_min_amount"] = _to_non_negative_decimal_or_none(
            withdraw.get("minAmount")
        ) or candidate.get("withdraw_min_amount")
        candidate["withdraw_max_amount"] = _to_non_negative_decimal_or_none(
            withdraw.get("maxAmount")
        ) or candidate.get("withdraw_max_amount")

        candidate["raw_fee_item"] = fee_item or {}

    return candidates


def sync_whitebit_provider_asset_contexts_from_raw(provider: Provider) -> SyncCounters:
    if provider.code != ProviderCode.WHITEBIT:
        raise ValueError("Этот сервис пока поддерживает только WHITEBIT.")

    asset_status_payload = _load_raw_json(provider.code, "asset_status_list")
    account_fees_payload = _load_raw_json(provider.code, "account_fees")

    try:
        maintenance_payload = _load_raw_json(provider.code, "maintenance_status")
    except FileNotFoundError:
        maintenance_payload = {}

    maintenance_status = _extract_maintenance_status(maintenance_payload)
    is_operational = _maintenance_is_operational(maintenance_status)

    account_fee_index = _extract_account_fee_index(account_fees_payload)
    candidates = _build_candidates(asset_status_payload, account_fee_index)

    stablecoin_codes = _get_stablecoin_codes()
    counters = SyncCounters()

    for candidate in candidates.values():
        if is_operational is False:
            candidate["AD"] = False
            candidate["AW"] = False
            candidate["status_note"] = "Platform maintenance"
        else:
            candidate["status_note"] = ""

        raw_metadata = {
            "provider_entity_code": candidate["provider_entity_code"],
            "asset_status_item": candidate.get("raw_asset_item") or {},
            "account_fee_item": candidate.get("raw_fee_item") or {},
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
            "AD": bool(candidate["AD"]),
            "AW": bool(candidate["AW"]),
            "status_note": candidate["status_note"],
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

        # ручные поля, кластер, is_front и match_status не трогаем
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
