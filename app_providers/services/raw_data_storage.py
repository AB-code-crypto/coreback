import json
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from app_providers.models import RawData, RawRequestStatus, RawRequestType
from app_providers.models.provider import Provider


def save_raw_json_to_file(*, provider_code: str, request_type: str, payload: object) -> str:
    now = timezone.now()
    relative_path = Path(
        "raw"
    ) / "providers" / provider_code / request_type / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d") / (
                            now.strftime("%Y%m%d_%H%M%S_%f") + ".json"
                    )

    full_path = Path(settings.BASE_DIR) / "storage" / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with full_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(relative_path)


def create_raw_data_record(
        *,
        provider: Provider,
        request_type: RawRequestType,
        source: str,
        http_status: int | None,
        requested_at,
        responded_at,
        file_path: str,
        request_status: RawRequestStatus,
        processing_error: str = "",
) -> RawData:
    return RawData.objects.create(
        provider=provider,
        request_type=request_type,
        request_status=request_status,
        source=source,
        http_status=http_status,
        requested_at=requested_at,
        responded_at=responded_at,
        file_path=file_path,
        is_processed=False,
        processing_error=processing_error,
    )
