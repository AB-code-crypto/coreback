from django.core.management.base import BaseCommand, CommandError

from app_providers.models.provider import Provider
from app_providers.models.raw_data import RawData, RawRequestStatus, RawRequestType
from app_providers.services.whitebit.assets_preview import (
    build_preview_from_raw_file,
    save_preview_file,
)


class Command(BaseCommand):
    help = "Build preview normalization report from the latest WhiteBIT raw assets file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider-code",
            default="whitebit",
            help="Provider code. Default: whitebit",
        )

    def handle(self, *args, **options):
        provider_code = options["provider_code"]

        try:
            provider = Provider.objects.get(code=provider_code)
        except Provider.DoesNotExist as exc:
            raise CommandError(f"Provider with code='{provider_code}' not found.") from exc

        raw_data = (
            RawData.objects.filter(
                provider=provider,
                request_type=RawRequestType.ASSETS,
                request_status=RawRequestStatus.SUCCESS,
            )
            .order_by("-created_at")
            .first()
        )

        if raw_data is None:
            raise CommandError(
                f"No successful RawData found for provider='{provider_code}' and request_type='assets'."
            )

        preview = build_preview_from_raw_file(raw_data.file_path)
        preview_file_path = save_preview_file(provider.code, preview)

        summary = preview["summary"]
        anomalies = preview["anomalies"]

        self.stdout.write(self.style.SUCCESS("WhiteBIT assets preview created successfully."))
        self.stdout.write(f"Source raw file: {raw_data.file_path}")
        self.stdout.write(f"Preview file:    {preview_file_path}")
        self.stdout.write("")

        self.stdout.write("Summary:")
        self.stdout.write(f"  Raw entities:              {summary['raw_entities_total']}")
        self.stdout.write(f"  Asset candidates:          {summary['asset_candidates_total']}")
        self.stdout.write(f"  Context candidates:        {summary['context_candidates_total']}")
        self.stdout.write(f"  AssetContext candidates:   {summary['asset_context_candidates_total']}")
        self.stdout.write(f"  Composite provider codes:  {summary['composite_codes_total']}")
        self.stdout.write("")

        self.stdout.write("Anomalies:")
        self.stdout.write(
            f"  default_not_in_operational_contexts: {len(anomalies['default_not_in_operational_contexts'])}"
        )
        self.stdout.write(
            f"  extra_confirmation_contexts:         {len(anomalies['extra_confirmation_contexts'])}"
        )
        self.stdout.write(
            f"  extra_limit_contexts:                {len(anomalies['extra_limit_contexts'])}"
        )
        self.stdout.write(
            f"  fiat_like_with_provider_contexts:    {len(anomalies['fiat_like_with_provider_contexts'])}"
        )
        self.stdout.write("")

        composite_sample = preview["composite_codes"][:10]
        if composite_sample:
            self.stdout.write("Composite code sample:")
            for item in composite_sample:
                self.stdout.write(
                    f"  {item['provider_code']} -> {item['asset_guess']} + {item['context_guess']}"
                )
