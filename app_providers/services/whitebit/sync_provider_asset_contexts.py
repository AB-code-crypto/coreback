from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app_assets.models import AssetContext
from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.provider_asset_context import ProviderAssetContext


@dataclass
class SyncCounters:
    created: int = 0
    updated: int = 0


def _to_int_zero(value):
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_decimal_zero(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _to_decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


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
            "deposit_confirmations": _to_int_zero(candidate.get("deposit_confirmations")),
            "withdraw_confirmations": _to_int_zero(candidate.get("withdraw_confirmations")),
            "deposit_fee_fixed": _to_decimal_zero(candidate.get("deposit_fee_fixed")),
            "deposit_fee_percent": _to_decimal_zero(candidate.get("deposit_fee_percent")),
            "deposit_fee_min_amount": _to_decimal_zero(candidate.get("deposit_fee_min_amount")),
            "deposit_fee_max_amount": _to_decimal_zero(candidate.get("deposit_fee_max_amount")),
            "withdraw_fee_fixed": _to_decimal_zero(candidate.get("withdraw_fee_fixed")),
            "withdraw_fee_percent": _to_decimal_zero(candidate.get("withdraw_fee_percent")),
            "withdraw_fee_min_amount": _to_decimal_zero(candidate.get("withdraw_fee_min_amount")),
            "withdraw_fee_max_amount": _to_decimal_zero(candidate.get("withdraw_fee_max_amount")),
            "deposit_min_amount": _to_decimal_or_none(candidate.get("deposit_min_amount")),
            "deposit_max_amount": _to_decimal_or_none(candidate.get("deposit_max_amount")),
            "withdraw_min_amount": _to_decimal_or_none(candidate.get("withdraw_min_amount")),
            "withdraw_max_amount": _to_decimal_or_none(candidate.get("withdraw_max_amount")),
        }

        obj, created = ProviderAssetContext.objects.get_or_create(
            provider=provider,
            asset_context=asset_context,
            defaults=defaults,
        )

        if created:
            counters.created += 1
            continue

        changed = False

        for field_name, new_value in defaults.items():
            old_value = getattr(obj, field_name)
            if old_value != new_value:
                setattr(obj, field_name, new_value)
                changed = True

        if changed:
            obj.save()
            counters.updated += 1

    return counters
