from app_providers.models.provider import Provider
from app_providers.models.provider_credential import ProviderCredential


def get_active_provider_credentials(provider: Provider):
    return provider.credentials.filter(is_active=True).order_by("priority", "created_at", "id")


def get_default_provider_credential(provider: Provider) -> ProviderCredential | None:
    return get_active_provider_credentials(provider).first()
