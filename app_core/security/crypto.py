from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def get_provider_credential_fernet() -> Fernet:
    key = getattr(settings, "PROVIDER_CREDENTIAL_MASTER_KEY", None)
    if not key:
        raise ImproperlyConfigured(
            "Не задан PROVIDER_CREDENTIAL_MASTER_KEY в настройках."
        )

    if isinstance(key, str):
        key = key.encode("utf-8")

    try:
        return Fernet(key)
    except Exception as exc:
        raise ImproperlyConfigured(
            "Некорректный PROVIDER_CREDENTIAL_MASTER_KEY."
        ) from exc


def encrypt_secret(value: str) -> str:
    if not value:
        return ""

    if not isinstance(value, str):
        value = str(value)

    fernet = get_provider_credential_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""

    if not isinstance(value, str):
        value = str(value)

    fernet = get_provider_credential_fernet()

    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "Не удалось расшифровать секрет. Проверь мастер-ключ или содержимое поля."
        ) from exc


def mask_secret(value: str | None, prefix: int = 3, suffix: int = 3) -> str:
    if not value:
        return "—"

    value = str(value)

    if len(value) <= prefix + suffix:
        return "*" * len(value)

    hidden_len = len(value) - prefix - suffix
    return f"{value[:prefix]}{'*' * hidden_len}{value[-suffix:]}"
