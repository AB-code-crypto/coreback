from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from app_core.models import UUIDTimestampedModel
from app_providers.models.provider import Provider
from app_core.security.crypto import decrypt_secret, encrypt_secret, mask_secret

from decimal import Decimal


class ProviderCredential(UUIDTimestampedModel):
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="credentials",
        verbose_name="Провайдер",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Название",
        help_text="Человекочитаемое название набора доступов.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активен",
        help_text="Разрешено ли использовать этот набор доступов.",
    )
    priority = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        db_index=True,
        verbose_name="Приоритет",
        help_text="Чем меньше число, тем выше приоритет этого набора доступов.",
    )
    api_key = models.TextField(
        blank=True,
        verbose_name="API Key",
        help_text="API Key провайдера. Хранится как текст, так как может быть очень длинным.",
    )
    api_secret = models.TextField(
        blank=True,
        verbose_name="API Secret",
        help_text="API Secret провайдера.",
    )
    api_passphrase = models.TextField(
        blank=True,
        verbose_name="API Passphrase",
        help_text="Дополнительная passphrase, если требуется провайдером.",
    )
    broker_key = models.TextField(
        blank=True,
        verbose_name="Broker Key",
        help_text="Broker key, если используется провайдером.",
    )
    trade_password = models.TextField(
        blank=True,
        verbose_name="Trade Password",
        help_text="Торговый пароль, если используется провайдером.",
    )

    is_ip_whitelist_enabled = models.BooleanField(
        default=False,
        verbose_name="Включён whitelist IP",
        help_text="Ограничен ли доступ к этому набору ключей по IP.",
    )
    allowed_ip_ranges = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Разрешённые IP/CIDR",
        help_text='Список разрешённых IP или CIDR, например: ["1.2.3.4/32", "5.6.7.0/24"].',
    )
    from decimal import Decimal

    spot_maker_fee = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        default=Decimal("0.001"),
        verbose_name="Spot maker fee",
        help_text="Торговая комиссия maker на споте. Хранится в виде доли. Пример: 0.001 = 0.1%, 0 = 0%, -0.0001 = -0.01%.",
    )

    spot_taker_fee = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        default=Decimal("0.001"),
        verbose_name="Spot taker fee",
        help_text="Торговая комиссия taker на споте. Хранится в виде доли. Пример: 0.001 = 0.1%, 0 = 0%, -0.0001 = -0.01%.",
    )

    futures_maker_fee = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        default=Decimal("0.001"),
        verbose_name="Futures maker fee",
        help_text="Торговая комиссия maker на фьючерсах. Хранится в виде доли. Пример: 0.001 = 0.1%, 0 = 0%, -0.0001 = -0.01%.",
    )

    futures_taker_fee = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        default=Decimal("0.001"),
        verbose_name="Futures taker fee",
        help_text="Торговая комиссия taker на фьючерсах. Хранится в виде доли. Пример: 0.001 = 0.1%, 0 = 0%, -0.0001 = -0.01%.",
    )

    fees_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата обновления комиссий",
        help_text="Когда комиссии были последний раз обновлены вручную или автоматически.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Свободная заметка администратора.",
    )

    class Meta:
        verbose_name = "Доступ"
        verbose_name_plural = "02 Доступы"
        ordering = ("provider", "priority", "name")
        indexes = [
            models.Index(fields=["provider", "is_active"], name="provcred_prov_active_idx"),
            models.Index(fields=["provider", "priority"], name="provcred_prov_prio_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "name"],
                name="uniq_providercredential_provider_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider.name} — {self.name}"

    def clean(self):
        if self.is_ip_whitelist_enabled and not self.allowed_ip_ranges:
            raise ValidationError(
                {"allowed_ip_ranges": "Укажите хотя бы один IP или CIDR, если whitelist включён."}
            )

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        if self.description:
            self.description = self.description.strip()
        super().save(*args, **kwargs)

    def _set_secret_value(self, field_name: str, value: str) -> None:
        value = (value or "").strip()
        encrypted_value = encrypt_secret(value) if value else ""
        setattr(self, field_name, encrypted_value)

    def _get_secret_value(self, field_name: str) -> str:
        value = getattr(self, field_name, "")
        return decrypt_secret(value) if value else ""

    def _get_masked_secret_value(self, field_name: str) -> str:
        return mask_secret(self._get_secret_value(field_name))

    def _has_secret_value(self, field_name: str) -> bool:
        return bool(getattr(self, field_name, ""))

    def set_api_key(self, value: str) -> None:
        self._set_secret_value("api_key", value)

    def get_api_key(self) -> str:
        return self._get_secret_value("api_key")

    def get_api_key_masked(self) -> str:
        return self._get_masked_secret_value("api_key")

    def has_api_key(self) -> bool:
        return self._has_secret_value("api_key")

    def set_api_secret(self, value: str) -> None:
        self._set_secret_value("api_secret", value)

    def get_api_secret(self) -> str:
        return self._get_secret_value("api_secret")

    def get_api_secret_masked(self) -> str:
        return self._get_masked_secret_value("api_secret")

    def has_api_secret(self) -> bool:
        return self._has_secret_value("api_secret")

    def set_api_passphrase(self, value: str) -> None:
        self._set_secret_value("api_passphrase", value)

    def get_api_passphrase(self) -> str:
        return self._get_secret_value("api_passphrase")

    def get_api_passphrase_masked(self) -> str:
        return self._get_masked_secret_value("api_passphrase")

    def has_api_passphrase(self) -> bool:
        return self._has_secret_value("api_passphrase")

    def set_broker_key(self, value: str) -> None:
        self._set_secret_value("broker_key", value)

    def get_broker_key(self) -> str:
        return self._get_secret_value("broker_key")

    def get_broker_key_masked(self) -> str:
        return self._get_masked_secret_value("broker_key")

    def has_broker_key(self) -> bool:
        return self._has_secret_value("broker_key")

    def set_trade_password(self, value: str) -> None:
        self._set_secret_value("trade_password", value)

    def get_trade_password(self) -> str:
        return self._get_secret_value("trade_password")

    def get_trade_password_masked(self) -> str:
        return self._get_masked_secret_value("trade_password")

    def has_trade_password(self) -> bool:
        return self._has_secret_value("trade_password")
