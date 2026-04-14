from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from app_providers.models.provider import Provider
from app_providers.services.raw_data_storage import save_raw_json_to_file
from app_providers.services.whitebit.client import WhitebitClient


@dataclass
class WhitebitRawFetchResult:
    success: bool
    file_path: str
    http_status: int | None = None
    requested_at: datetime | None = None
    responded_at: datetime | None = None
    error_message: str = ""


def fetch_whitebit_assets(provider: Provider) -> WhitebitRawFetchResult:
    client = WhitebitClient()
    requested_at = timezone.now()

    try:
        assets_response = client.fetch_assets()
        fees_response = client.fetch_fee()
        responded_at = timezone.now()

        payload = {
            "assets": assets_response.payload,
            "fees": fees_response.payload,
        }

        file_path = save_raw_json_to_file(
            provider_code=provider.code,
            request_type="assets",
            payload=payload,
        )

        return WhitebitRawFetchResult(
            success=True,
            file_path=file_path,
            http_status=assets_response.http_status,
            requested_at=requested_at,
            responded_at=responded_at,
            error_message="",
        )

    except Exception as exc:
        responded_at = timezone.now()

        error_payload = {
            "error": str(exc),
        }

        file_path = save_raw_json_to_file(
            provider_code=provider.code,
            request_type="assets",
            payload=error_payload,
        )

        return WhitebitRawFetchResult(
            success=False,
            file_path=file_path,
            http_status=None,
            requested_at=requested_at,
            responded_at=responded_at,
            error_message=str(exc),
        )
