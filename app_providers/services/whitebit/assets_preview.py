import json
from pathlib import Path

from django.conf import settings


def resolve_raw_file_path(file_path: str) -> Path:
    path = Path(file_path)

    if path.is_absolute():
        return path

    candidates = [
        Path(settings.BASE_DIR) / "storage" / path,
        Path(settings.BASE_DIR) / path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def load_raw_payload(file_path: str) -> dict:
    resolved_path = resolve_raw_file_path(file_path)

    with resolved_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError("WhiteBIT assets payload must be a JSON object.")

    return payload


def get_operational_networks(item: dict) -> tuple[set[str], set[str]]:
    networks = item.get("networks") or {}

    deposits = set(networks.get("deposits") or [])
    withdraws = set(networks.get("withdraws") or [])

    return deposits, withdraws


def get_provider_contexts(item: dict) -> tuple[set[str], set[str]]:
    providers = item.get("providers") or {}

    deposits = set(providers.get("deposits") or [])
    withdraws = set(providers.get("withdraws") or [])

    return deposits, withdraws


def get_confirmation_contexts(item: dict) -> set[str]:
    confirmations = item.get("confirmations") or {}
    return set(confirmations.keys())


def get_limit_contexts(item: dict) -> set[str]:
    limits = item.get("limits") or {}

    result = set()
    for direction in ("deposit", "withdraw"):
        result.update((limits.get(direction) or {}).keys())

    return result


def is_composite_code(code: str, all_codes: set[str]) -> bool:
    if "_" not in code:
        return False

    base_code = code.split("_", 1)[0]
    return base_code in all_codes


def build_asset_candidates(payload: dict) -> dict:
    all_codes = set(payload.keys())

    asset_candidates = {}
    context_candidates = {}
    asset_context_candidates = {}
    composite_codes = []
    anomalies = {
        "default_not_in_operational_contexts": [],
        "extra_confirmation_contexts": [],
        "extra_limit_contexts": [],
        "fiat_like_with_provider_contexts": [],
    }

    for code, item in payload.items():
        if not isinstance(item, dict):
            continue

        name = item.get("name") or code

        deposit_networks, withdraw_networks = get_operational_networks(item)
        provider_deposits, provider_withdraws = get_provider_contexts(item)

        operational_networks = deposit_networks | withdraw_networks
        provider_contexts = provider_deposits | provider_withdraws

        default_context = ((item.get("networks") or {}).get("default")) or ""
        confirmation_contexts = get_confirmation_contexts(item)
        limit_contexts = get_limit_contexts(item)

        composite = is_composite_code(code, all_codes)
        fiat_like = bool(provider_contexts)

        if composite:
            base_code, context_guess = code.split("_", 1)
            composite_codes.append(
                {
                    "provider_code": code,
                    "name": name,
                    "asset_guess": base_code,
                    "context_guess": context_guess,
                    "can_deposit": item.get("can_deposit", False),
                    "can_withdraw": item.get("can_withdraw", False),
                }
            )
            continue

        asset_candidates[code] = {
            "code": code,
            "name_long": name,
            "kind": "fiat_like" if fiat_like else "crypto_like",
            "can_deposit": item.get("can_deposit", False),
            "can_withdraw": item.get("can_withdraw", False),
        }

        if fiat_like:
            anomalies["fiat_like_with_provider_contexts"].append(
                {
                    "asset_code": code,
                    "provider_contexts": sorted(provider_contexts),
                }
            )

            for context_code in sorted(provider_contexts):
                context_candidates.setdefault(
                    context_code,
                    {
                        "code": context_code,
                        "source_kind": "provider",
                    },
                )

                candidate_code = f"{code}__{context_code}"
                asset_context_candidates[candidate_code] = {
                    "code": candidate_code,
                    "asset_code": code,
                    "context_code": context_code,
                    "deposit_enabled": context_code in provider_deposits,
                    "withdraw_enabled": context_code in provider_withdraws,
                    "source_kind": "provider",
                }

            continue

        for context_code in sorted(operational_networks):
            context_candidates.setdefault(
                context_code,
                {
                    "code": context_code,
                    "source_kind": "network",
                },
            )

            candidate_code = f"{code}__{context_code}"
            asset_context_candidates[candidate_code] = {
                "code": candidate_code,
                "asset_code": code,
                "context_code": context_code,
                "deposit_enabled": context_code in deposit_networks,
                "withdraw_enabled": context_code in withdraw_networks,
                "source_kind": "network",
            }

        if default_context and default_context not in operational_networks:
            anomalies["default_not_in_operational_contexts"].append(
                {
                    "asset_code": code,
                    "default_context": default_context,
                    "operational_contexts": sorted(operational_networks),
                }
            )

        extra_confirmation_contexts = sorted(confirmation_contexts - operational_networks)
        if extra_confirmation_contexts:
            anomalies["extra_confirmation_contexts"].append(
                {
                    "asset_code": code,
                    "extra_contexts": extra_confirmation_contexts,
                    "operational_contexts": sorted(operational_networks),
                }
            )

        extra_limit_contexts = sorted(limit_contexts - operational_networks)
        if extra_limit_contexts:
            anomalies["extra_limit_contexts"].append(
                {
                    "asset_code": code,
                    "extra_contexts": extra_limit_contexts,
                    "operational_contexts": sorted(operational_networks),
                }
            )

    return {
        "summary": {
            "raw_entities_total": len(payload),
            "asset_candidates_total": len(asset_candidates),
            "context_candidates_total": len(context_candidates),
            "asset_context_candidates_total": len(asset_context_candidates),
            "composite_codes_total": len(composite_codes),
        },
        "asset_candidates": sorted(asset_candidates.values(), key=lambda x: x["code"]),
        "context_candidates": sorted(context_candidates.values(), key=lambda x: x["code"]),
        "asset_context_candidates": sorted(asset_context_candidates.values(), key=lambda x: x["code"]),
        "composite_codes": sorted(composite_codes, key=lambda x: x["provider_code"]),
        "anomalies": anomalies,
    }


def save_preview_file(provider_code: str, preview_data: dict) -> str:
    relative_path = Path("raw") / provider_code / "assets_preview.json"
    full_path = Path(settings.BASE_DIR) / "storage" / relative_path

    full_path.parent.mkdir(parents=True, exist_ok=True)

    with full_path.open("w", encoding="utf-8") as f:
        json.dump(preview_data, f, ensure_ascii=False, indent=2)

    return str(relative_path)


def build_preview_from_raw_file(file_path: str) -> dict:
    payload = load_raw_payload(file_path)
    return build_asset_candidates(payload)
