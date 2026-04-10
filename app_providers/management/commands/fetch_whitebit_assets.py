from django.core.management.base import BaseCommand, CommandError

from app_providers.models.provider import Provider
from app_providers.services.whitebit.fetch_assets import fetch_whitebit_assets


class Command(BaseCommand):
    help = "Fetch raw asset availability data from WhiteBIT and save it to file + RawData."

    def add_arguments(self, parser):
        parser.add_argument("--provider-code", required=True)

    def handle(self, *args, **options):
        provider_code = options["provider_code"]

        try:
            provider = Provider.objects.get(code=provider_code)
        except Provider.DoesNotExist as exc:
            raise CommandError(f"Provider with code='{provider_code}' not found.") from exc

        raw_data = fetch_whitebit_assets(provider)

        self.stdout.write(
            self.style.SUCCESS(
                f"RawData created: id={raw_data.id}, status={raw_data.request_status}, file={raw_data.file_path}"
            )
        )
