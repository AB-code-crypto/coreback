from dataclasses import dataclass

from app_assets.models.asset import Asset, AssetType
from app_assets.models.context import Context, ContextType
from app_assets.models.asset_context import AssetContext


@dataclass
class SyncCounters:
    created: int = 0
    updated: int = 0


@dataclass
class WhitebitAssetsSyncResult:
    assets: SyncCounters
    contexts: SyncCounters
    asset_contexts: SyncCounters


def _pick_asset_type(kind: str) -> str:
    if kind == "fiat_like":
        return AssetType.FIAT
    if kind == "crypto_like":
        return AssetType.CRYPTO
    return AssetType.OTHER


def _pick_context_type(source_kind: str) -> str:
    if source_kind == "network":
        return ContextType.BLOCKCHAIN
    if source_kind == "provider":
        return ContextType.OTHER
    return ContextType.OTHER


def _sync_asset(candidate: dict, counters: SyncCounters) -> Asset:
    code = candidate["code"]
    name_long = candidate["name_long"]
    asset_type = _pick_asset_type(candidate.get("kind", ""))

    defaults = {
        "name_short": code,
        "name_long": name_long,
        "asset_type": asset_type,
        "is_active": True,
    }

    obj, created = Asset.objects.get_or_create(code=code, defaults=defaults)

    if created:
        counters.created += 1
        return obj

    changed = False

    if obj.name_short != defaults["name_short"]:
        obj.name_short = defaults["name_short"]
        changed = True

    if obj.name_long != defaults["name_long"]:
        obj.name_long = defaults["name_long"]
        changed = True

    if obj.asset_type != defaults["asset_type"]:
        obj.asset_type = defaults["asset_type"]
        changed = True

    if obj.is_active is not True:
        obj.is_active = True
        changed = True

    if changed:
        obj.save()
        counters.updated += 1

    return obj


def _sync_context(candidate: dict, counters: SyncCounters) -> Context:
    code = candidate["code"]
    context_type = _pick_context_type(candidate.get("source_kind", ""))

    defaults = {
        "name_short": code,
        "name_long": code,
        "context_type": context_type,
        "is_active": True,
    }

    obj, created = Context.objects.get_or_create(code=code, defaults=defaults)

    if created:
        counters.created += 1
        return obj

    changed = False

    if obj.name_short != defaults["name_short"]:
        obj.name_short = defaults["name_short"]
        changed = True

    if obj.name_long != defaults["name_long"]:
        obj.name_long = defaults["name_long"]
        changed = True

    if obj.context_type != defaults["context_type"]:
        obj.context_type = defaults["context_type"]
        changed = True

    if obj.is_active is not True:
        obj.is_active = True
        changed = True

    if changed:
        obj.save()
        counters.updated += 1

    return obj


def _sync_asset_context(candidate: dict, counters: SyncCounters) -> AssetContext:
    asset = Asset.objects.get(code=candidate["asset_code"])
    context = Context.objects.get(code=candidate["context_code"])

    obj, created = AssetContext.objects.get_or_create(
        asset=asset,
        context=context,
        defaults={"is_active": True},
    )

    if created:
        counters.created += 1
        return obj

    if obj.is_active is not True:
        obj.is_active = True
        obj.save()
        counters.updated += 1

    return obj


def sync_whitebit_assets_from_preview(preview: dict) -> WhitebitAssetsSyncResult:
    asset_counters = SyncCounters()
    context_counters = SyncCounters()
    asset_context_counters = SyncCounters()

    for candidate in preview.get("asset_candidates", []):
        _sync_asset(candidate, asset_counters)

    for candidate in preview.get("context_candidates", []):
        _sync_context(candidate, context_counters)

    for candidate in preview.get("asset_context_candidates", []):
        _sync_asset_context(candidate, asset_context_counters)

    return WhitebitAssetsSyncResult(
        assets=asset_counters,
        contexts=context_counters,
        asset_contexts=asset_context_counters,
    )