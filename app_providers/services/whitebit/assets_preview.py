import json
from decimal import Decimal, InvalidOperation
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


def get_assets_payload(payload: dict) -> dict:
    assets = payload.get("assets")
    if isinstance(assets, dict):
        return assets
    return payload


def get_fees_payload(payload: dict):
    fees = payload.get("fees")

    if isinstance(fees, (dict, list)):
        return fees

    return {}


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


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_decimal_str(value):
    if value in (None, ""):
        return None
    try:
        return str(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _extract_confirmations(item: dict, context_code: str) -> tuple[int | None, int | None]:
    confirmations = item.get("confirmations") or {}
    raw_value = confirmations.get(context_code)

    if raw_value is None:
        return None, None

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
        return _to_int(deposit_value), _to_int(withdraw_value)

    value = _to_int(raw_value)
    return value, value


def _extract_amount_limits(item: dict, context_code: str, direction: str) -> tuple[str | None, str | None]:
    limits = item.get("limits") or {}
    direction_limits = (limits.get(direction) or {}).get(context_code) or {}

    if not isinstance(direction_limits, dict):
        return None, None

    min_amount = _to_decimal_str(direction_limits.get("min") or direction_limits.get("min_amount"))
    max_amount = _to_decimal_str(direction_limits.get("max") or direction_limits.get("max_amount"))

    return min_amount, max_amount


def _build_private_fee_index(fees_payload) -> dict[str, dict]:
    if not isinstance(fees_payload, list):
        return {}

    result = {}

    for item in fees_payload:
        if not isinstance(item, dict):
            continue

        ticker = str(item.get("ticker") or "").strip().upper()
        if not ticker:
            continue

        result[ticker] = item

    return result


def _extract_fee_info_for_context(
        fees_payload,
        asset_code: str,
        context_code: str,
        direction: str,
        private_fee_index: dict[str, dict] | None = None,
) -> dict:
    # Новый private WhiteBIT format: list[{"ticker": "...", "deposit": {...}, "withdraw": {...}}]
    if isinstance(fees_payload, list):
        if private_fee_index is None:
            private_fee_index = _build_private_fee_index(fees_payload)

        asset_fee_info = private_fee_index.get(asset_code.upper()) or {}
        direction_info = asset_fee_info.get(direction) or {}

        if not isinstance(direction_info, dict):
            return {}

        fixed = _to_decimal_str(direction_info.get("fixed"))
        percent = _to_decimal_str(direction_info.get("percentFlex") or direction_info.get("flex"))
        min_fee_amount = _to_decimal_str(direction_info.get("minFlex"))
        max_fee_amount = _to_decimal_str(direction_info.get("maxFlex"))
        min_amount = _to_decimal_str(direction_info.get("minAmount") or direction_info.get("min_amount"))
        max_amount = _to_decimal_str(direction_info.get("maxAmount") or direction_info.get("max_amount"))

        return {
            f"{direction}_fee_fixed": fixed,
            f"{direction}_fee_percent": percent,
            f"{direction}_fee_min_amount": min_fee_amount,
            f"{direction}_fee_max_amount": max_fee_amount,
            f"{direction}_min_amount": min_amount,
            f"{direction}_max_amount": max_amount,
        }

    # Старый dict format оставляем для обратной совместимости
    if not isinstance(fees_payload, dict):
        return {}

    asset_fee_info = fees_payload.get(asset_code) or {}
    direction_info = asset_fee_info.get(direction) or {}

    if not isinstance(direction_info, dict):
        return {}

    # crypto-like format: flat object on asset level
    if any(key in direction_info for key in ("fixed", "flex", "min_amount", "max_amount")):
        fee_info = direction_info
    else:
        # provider/fiat-like format: nested by provider/context code
        fee_info = direction_info.get(context_code) or {}

    if not isinstance(fee_info, dict):
        return {}

    fixed = _to_decimal_str(fee_info.get("fixed"))
    percent = _to_decimal_str(fee_info.get("flex"))
    min_amount = _to_decimal_str(fee_info.get("min_amount"))
    max_amount = _to_decimal_str(fee_info.get("max_amount"))

    return {
        f"{direction}_fee_fixed": fixed,
        f"{direction}_fee_percent": percent,
        f"{direction}_fee_min_amount": None,
        f"{direction}_fee_max_amount": None,
        f"{direction}_min_amount": min_amount,
        f"{direction}_max_amount": max_amount,
    }


def build_asset_candidates(payload: dict) -> dict:
    assets_payload = get_assets_payload(payload)
    fees_payload = get_fees_payload(payload)
    private_fee_index = _build_private_fee_index(fees_payload)

    all_codes = set(assets_payload.keys())

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

    for code, item in assets_payload.items():
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

                deposit_confirmations, withdraw_confirmations = _extract_confirmations(item, context_code)
                deposit_min_amount, deposit_max_amount = _extract_amount_limits(item, context_code, "deposit")
                withdraw_min_amount, withdraw_max_amount = _extract_amount_limits(item, context_code, "withdraw")
                deposit_fee_info = _extract_fee_info_for_context(
                    fees_payload,
                    code,
                    context_code,
                    "deposit",
                    private_fee_index=private_fee_index,
                )
                withdraw_fee_info = _extract_fee_info_for_context(
                    fees_payload,
                    code,
                    context_code,
                    "withdraw",
                    private_fee_index=private_fee_index,
                )

                candidate_code = f"{code}__{context_code}"
                asset_context_candidates[candidate_code] = {
                    "code": candidate_code,
                    "asset_code": code,
                    "context_code": context_code,
                    "deposit_enabled": context_code in provider_deposits,
                    "withdraw_enabled": context_code in provider_withdraws,
                    "source_kind": "provider",
                    "deposit_confirmations": deposit_confirmations,
                    "withdraw_confirmations": withdraw_confirmations,
                    "deposit_min_amount": deposit_fee_info.get("deposit_min_amount") or deposit_min_amount,
                    "deposit_max_amount": deposit_fee_info.get("deposit_max_amount") or deposit_max_amount,
                    "withdraw_min_amount": withdraw_fee_info.get("withdraw_min_amount") or withdraw_min_amount,
                    "withdraw_max_amount": withdraw_fee_info.get("withdraw_max_amount") or withdraw_max_amount,
                    **deposit_fee_info,
                    **withdraw_fee_info,
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

            deposit_confirmations, withdraw_confirmations = _extract_confirmations(item, context_code)
            deposit_min_amount, deposit_max_amount = _extract_amount_limits(item, context_code, "deposit")
            withdraw_min_amount, withdraw_max_amount = _extract_amount_limits(item, context_code, "withdraw")
            deposit_fee_info = _extract_fee_info_for_context(
                fees_payload,
                code,
                context_code,
                "deposit",
                private_fee_index=private_fee_index,
            )
            withdraw_fee_info = _extract_fee_info_for_context(
                fees_payload,
                code,
                context_code,
                "withdraw",
                private_fee_index=private_fee_index,
            )

            candidate_code = f"{code}__{context_code}"
            asset_context_candidates[candidate_code] = {
                "code": candidate_code,
                "asset_code": code,
                "context_code": context_code,
                "deposit_enabled": context_code in deposit_networks,
                "withdraw_enabled": context_code in withdraw_networks,
                "source_kind": "network",
                "deposit_confirmations": deposit_confirmations,
                "withdraw_confirmations": withdraw_confirmations,
                "deposit_min_amount": deposit_fee_info.get("deposit_min_amount") or deposit_min_amount,
                "deposit_max_amount": deposit_fee_info.get("deposit_max_amount") or deposit_max_amount,
                "withdraw_min_amount": withdraw_fee_info.get("withdraw_min_amount") or withdraw_min_amount,
                "withdraw_max_amount": withdraw_fee_info.get("withdraw_max_amount") or withdraw_max_amount,
                **deposit_fee_info,
                **withdraw_fee_info,
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
            "raw_entities_total": len(assets_payload),
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
