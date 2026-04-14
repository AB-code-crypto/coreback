import json
from pathlib import Path

from django.conf import settings


def get_raw_relative_path(provider_code: str, request_type: str) -> str:
    return str(Path("raw") / provider_code / f"{request_type}.json")


def get_raw_full_path(provider_code: str, request_type: str) -> Path:
    relative_path = get_raw_relative_path(provider_code, request_type)
    return Path(settings.BASE_DIR) / "storage" / relative_path


def save_raw_json_to_file(*, provider_code: str, request_type: str, payload: object) -> str:
    full_path = get_raw_full_path(provider_code=provider_code, request_type=request_type)
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with full_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return get_raw_relative_path(provider_code=provider_code, request_type=request_type)
