from dataclasses import dataclass


@dataclass(frozen=True)
class SupportedProviderSpec:
    code: str
    name: str
    provider_type: str
    affiliate_url: str = ""


SUPPORTED_PROVIDERS: dict[str, SupportedProviderSpec] = {
    "whitebit": SupportedProviderSpec(
        code="whitebit",
        name="WhiteBIT",
        provider_type="exchange",
        affiliate_url="",
    ),
    "mexc": SupportedProviderSpec(
        code="mexc",
        name="MEXC",
        provider_type="exchange",
        affiliate_url="",
    ),
    # сюда потом будут добавляться новые реально поддержанные провайдеры
}


def normalize_provider_code(code: str) -> str:
    return (code or "").strip().lower()


def get_supported_provider_spec(code: str) -> SupportedProviderSpec | None:
    return SUPPORTED_PROVIDERS.get(normalize_provider_code(code))


def get_supported_provider_choices() -> list[tuple[str, str]]:
    return [
        (spec.code, spec.name)
        for spec in SUPPORTED_PROVIDERS.values()
    ]
