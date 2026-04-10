from django.utils import timezone

from app_providers.models import RawRequestStatus, RawRequestType
from app_providers.models.provider import Provider
from app_providers.services.raw_data_storage import (
    create_raw_data_record,
    save_raw_json_to_file,
)
from app_providers.services.whitebit.client import WhitebitClient


def fetch_whitebit_assets(provider: Provider):
    client = WhitebitClient()
    requested_at = timezone.now()

    try:
        response = client.fetch_assets()
        responded_at = timezone.now()

        file_path = save_raw_json_to_file(
            provider_code=provider.code,
            request_type=RawRequestType.ASSETS,
            payload=response.payload,
        )

        return create_raw_data_record(
            provider=provider,
            request_type=RawRequestType.ASSETS,
            source="whitebit.public.assets",
            http_status=response.http_status,
            requested_at=requested_at,
            responded_at=responded_at,
            file_path=file_path,
            request_status=RawRequestStatus.SUCCESS,
        )

    except Exception as exc:
        responded_at = timezone.now()

        # при ошибке тоже можно сохранить минимальный error-payload в файл
        error_payload = {
            "error": str(exc),
        }

        file_path = save_raw_json_to_file(
            provider_code=provider.code,
            request_type=RawRequestType.ASSETS,
            payload=error_payload,
        )

        return create_raw_data_record(
            provider=provider,
            request_type=RawRequestType.ASSETS,
            source="whitebit.public.assets",
            http_status=None,
            requested_at=requested_at,
            responded_at=responded_at,
            file_path=file_path,
            request_status=RawRequestStatus.FAILED,
            processing_error=str(exc),
        )
