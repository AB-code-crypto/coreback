from dataclasses import dataclass

from app_assets.models import AssetContext
from app_providers.models.provider import Provider, ProviderCode
from app_providers.models.provider_asset_context import ProviderAssetContext


@dataclass
class SyncCounters:
    created: int = 0
    updated: int = 0


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
            "provider_name": "",
            "is_active": True,
            "deposit_enabled": bool(candidate.get("deposit_enabled", False)),
            "withdraw_enabled": bool(candidate.get("withdraw_enabled", False)),
        }

        obj, created = ProviderAssetContext.objects.get_or_create(
            provider=provider,
            asset_context=asset_context,
            defaults={
                "provider_code": asset_context_code,
                **defaults,
            },
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

        if changed:
            obj.save()
            counters.updated += 1

    return counters
