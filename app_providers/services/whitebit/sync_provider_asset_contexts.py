from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app_assets.models import AssetContext
from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.provider_asset_context import (
    ProviderAssetContext,
    ProviderTransferFeeType,
)


@dataclass
class SyncCounters:
    created: int = 0
    updated: int = 0


def _to_bool(value):
    if value is None:
        return None
    return bool(value)


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_decimal(value):
    if value in (None, ""):
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_fee_type(value):
    if not value:
        return None

    value = str(value).strip().lower()
    allowed = {
        ProviderTransferFeeType.NONE,
        ProviderTransferFeeType.FIXED,
        ProviderTransferFeeType.PERCENT,
    }
    if value in allowed:
        return value

    return None


def _apply_if_present(obj, candidate: dict, candidate_key: str, field_name: str) -> bool:
    if candidate_key not in candidate:
        return False

    new_value = candidate[candidate_key]
    old_value = getattr(obj, field_name)

    if old_value != new_value:
        setattr(obj, field_name, new_value)
        return True

    return False


def sync_whitebit_provider_asset_contexts_from_preview(
        provider: Provider,
        preview: dict,
) -> SyncCounters:
    if provider.code != ProviderCode.WHITEBIT:
        raise ValueError("Этот сервис пока поддерживает только WHITEBIT.")

    counters = SyncCounters()

    for candidate in preview.get("asset_context_candidates", []):
        asset_context_code = candidate["code"]
        asset_context = AssetContext.objects.get(code=asset_context_code)

        defaults = {
            "provider_code": asset_context_code,
            "is_active": True,
            "deposit_enabled": bool(candidate.get("deposit_enabled", False)),
            "withdraw_enabled": bool(candidate.get("withdraw_enabled", False)),
        }

        # Новые поля добавляем в defaults только если они реально пришли из preview
        if "deposit_confirmations" in candidate:
            defaults["deposit_confirmations"] = _to_int(candidate.get("deposit_confirmations"))

        if "withdraw_confirmations" in candidate:
            defaults["withdraw_confirmations"] = _to_int(candidate.get("withdraw_confirmations"))

        if "deposit_fee_type" in candidate:
            fee_type = _to_fee_type(candidate.get("deposit_fee_type"))
            if fee_type is not None:
                defaults["deposit_fee_type"] = fee_type

        if "deposit_fee_fixed" in candidate:
            defaults["deposit_fee_fixed"] = _to_decimal(candidate.get("deposit_fee_fixed"))

        if "deposit_fee_percent" in candidate:
            defaults["deposit_fee_percent"] = _to_decimal(candidate.get("deposit_fee_percent"))

        if "deposit_fee_min_amount" in candidate:
            defaults["deposit_fee_min_amount"] = _to_decimal(candidate.get("deposit_fee_min_amount"))

        if "deposit_fee_max_amount" in candidate:
            defaults["deposit_fee_max_amount"] = _to_decimal(candidate.get("deposit_fee_max_amount"))

        if "withdraw_fee_type" in candidate:
            fee_type = _to_fee_type(candidate.get("withdraw_fee_type"))
            if fee_type is not None:
                defaults["withdraw_fee_type"] = fee_type

        if "withdraw_fee_fixed" in candidate:
            defaults["withdraw_fee_fixed"] = _to_decimal(candidate.get("withdraw_fee_fixed"))

        if "withdraw_fee_percent" in candidate:
            defaults["withdraw_fee_percent"] = _to_decimal(candidate.get("withdraw_fee_percent"))

        if "withdraw_fee_min_amount" in candidate:
            defaults["withdraw_fee_min_amount"] = _to_decimal(candidate.get("withdraw_fee_min_amount"))

        if "withdraw_fee_max_amount" in candidate:
            defaults["withdraw_fee_max_amount"] = _to_decimal(candidate.get("withdraw_fee_max_amount"))

        if "deposit_min_amount" in candidate:
            defaults["deposit_min_amount"] = _to_decimal(candidate.get("deposit_min_amount"))

        if "deposit_max_amount" in candidate:
            defaults["deposit_max_amount"] = _to_decimal(candidate.get("deposit_max_amount"))

        if "withdraw_min_amount" in candidate:
            defaults["withdraw_min_amount"] = _to_decimal(candidate.get("withdraw_min_amount"))

        if "withdraw_max_amount" in candidate:
            defaults["withdraw_max_amount"] = _to_decimal(candidate.get("withdraw_max_amount"))

        obj, created = ProviderAssetContext.objects.get_or_create(
            provider=provider,
            asset_context=asset_context,
            defaults=defaults,
        )

        if created:
            counters.created += 1
            continue

        changed = False

        if obj.provider_code != asset_context_code:
            obj.provider_code = asset_context_code
            changed = True

        if obj.is_active is not True:
            obj.is_active = True
            changed = True

        deposit_enabled = bool(candidate.get("deposit_enabled", False))
        if obj.deposit_enabled != deposit_enabled:
            obj.deposit_enabled = deposit_enabled
            changed = True

        withdraw_enabled = bool(candidate.get("withdraw_enabled", False))
        if obj.withdraw_enabled != withdraw_enabled:
            obj.withdraw_enabled = withdraw_enabled
            changed = True

        # Новые поля обновляем только если ключ реально пришёл из preview
        if "deposit_confirmations" in candidate:
            new_value = _to_int(candidate.get("deposit_confirmations"))
            if obj.deposit_confirmations != new_value:
                obj.deposit_confirmations = new_value
                changed = True

        if "withdraw_confirmations" in candidate:
            new_value = _to_int(candidate.get("withdraw_confirmations"))
            if obj.withdraw_confirmations != new_value:
                obj.withdraw_confirmations = new_value
                changed = True

        if "deposit_fee_type" in candidate:
            new_value = _to_fee_type(candidate.get("deposit_fee_type"))
            if new_value is not None and obj.deposit_fee_type != new_value:
                obj.deposit_fee_type = new_value
                changed = True

        if "deposit_fee_fixed" in candidate:
            new_value = _to_decimal(candidate.get("deposit_fee_fixed"))
            if obj.deposit_fee_fixed != new_value:
                obj.deposit_fee_fixed = new_value
                changed = True

        if "deposit_fee_percent" in candidate:
            new_value = _to_decimal(candidate.get("deposit_fee_percent"))
            if obj.deposit_fee_percent != new_value:
                obj.deposit_fee_percent = new_value
                changed = True

        if "deposit_fee_min_amount" in candidate:
            new_value = _to_decimal(candidate.get("deposit_fee_min_amount"))
            if obj.deposit_fee_min_amount != new_value:
                obj.deposit_fee_min_amount = new_value
                changed = True

        if "deposit_fee_max_amount" in candidate:
            new_value = _to_decimal(candidate.get("deposit_fee_max_amount"))
            if obj.deposit_fee_max_amount != new_value:
                obj.deposit_fee_max_amount = new_value
                changed = True

        if "withdraw_fee_type" in candidate:
            new_value = _to_fee_type(candidate.get("withdraw_fee_type"))
            if new_value is not None and obj.withdraw_fee_type != new_value:
                obj.withdraw_fee_type = new_value
                changed = True

        if "withdraw_fee_fixed" in candidate:
            new_value = _to_decimal(candidate.get("withdraw_fee_fixed"))
            if obj.withdraw_fee_fixed != new_value:
                obj.withdraw_fee_fixed = new_value
                changed = True

        if "withdraw_fee_percent" in candidate:
            new_value = _to_decimal(candidate.get("withdraw_fee_percent"))
            if obj.withdraw_fee_percent != new_value:
                obj.withdraw_fee_percent = new_value
                changed = True

        if "withdraw_fee_min_amount" in candidate:
            new_value = _to_decimal(candidate.get("withdraw_fee_min_amount"))
            if obj.withdraw_fee_min_amount != new_value:
                obj.withdraw_fee_min_amount = new_value
                changed = True

        if "withdraw_fee_max_amount" in candidate:
            new_value = _to_decimal(candidate.get("withdraw_fee_max_amount"))
            if obj.withdraw_fee_max_amount != new_value:
                obj.withdraw_fee_max_amount = new_value
                changed = True

        if "deposit_min_amount" in candidate:
            new_value = _to_decimal(candidate.get("deposit_min_amount"))
            if obj.deposit_min_amount != new_value:
                obj.deposit_min_amount = new_value
                changed = True

        if "deposit_max_amount" in candidate:
            new_value = _to_decimal(candidate.get("deposit_max_amount"))
            if obj.deposit_max_amount != new_value:
                obj.deposit_max_amount = new_value
                changed = True

        if "withdraw_min_amount" in candidate:
            new_value = _to_decimal(candidate.get("withdraw_min_amount"))
            if obj.withdraw_min_amount != new_value:
                obj.withdraw_min_amount = new_value
                changed = True

        if "withdraw_max_amount" in candidate:
            new_value = _to_decimal(candidate.get("withdraw_max_amount"))
            if obj.withdraw_max_amount != new_value:
                obj.withdraw_max_amount = new_value
                changed = True

        if changed:
            obj.save()
            counters.updated += 1

    return counters
