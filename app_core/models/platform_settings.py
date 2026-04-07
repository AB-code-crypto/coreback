from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import TimestampedModel
from app_core.config.default_data import DEFAULT_STABLECOIN_CODES, DEFAULT_FIAT_CURRENCY_CODES, DEFAULT_MEMO_TAG_NETWORK_CODES


class MaintenanceReason(models.TextChoices):
    TECHNICAL_WORKS = "technical_works", "Технические работы"
    PROVIDER_ISSUES = "provider_issues", "Проблемы с провайдерами"
    DATA_SYNC_ISSUES = "data_sync_issues", "Проблемы с синхронизацией данных"
    MANUAL_MODE = "manual_mode", "Переход в ручной режим"


class PlatformSettings(TimestampedModel):
    stablecoin_codes = models.TextField(
        default=DEFAULT_STABLECOIN_CODES,
        blank=True,
        verbose_name="Коды стейблкоинов",
        help_text=(
            "Список кодов стейблкоинов. Можно вводить через запятую или с новой строки. "
            "При сохранении список будет очищен от дублей, отсортирован по алфавиту "
            "и сохранён в одну строку через запятую и пробел. Регистр не изменяется."
        ),
    )
    fiat_currency_codes = models.TextField(
        default=DEFAULT_FIAT_CURRENCY_CODES,
        blank=True,
        verbose_name="Коды фиатных валют",
        help_text=(
            "Список кодов фиатных валют. Можно вводить через запятую или с новой строки. "
            "При сохранении список будет очищен от дублей, отсортирован по алфавиту "
            "и сохранён в одну строку через запятую и пробел. Регистр не изменяется."
        ),
    )
    memo_tag_network_codes = models.TextField(
        default=DEFAULT_MEMO_TAG_NETWORK_CODES,
        blank=True,
        verbose_name="Коды сетей с MEMO/TAG",
        help_text=(
            "Список кодов сетей, где для перевода требуется MEMO, TAG, Destination Tag или аналогичное поле. "
            "Можно вводить через запятую или с новой строки. При сохранении список будет очищен от дублей, "
            "отсортирован по алфавиту и сохранён в одну строку через запятую и пробел. Регистр не изменяется."
        ),
    )
    maintenance_mode_enabled = models.BooleanField(
        default=False,
        verbose_name="Режим технических работ",
        help_text=(
            "Если включено, ядро сообщает downstream-сервисам, что работает в режиме паузы "
            "или ограниченной доступности."
        ),
    )

    maintenance_reason = models.CharField(
        max_length=64,
        choices=MaintenanceReason.choices,
        blank=True,
        verbose_name="Причина технических работ",
        help_text="Короткая стандартная причина включения режима технических работ.",
    )

    telegram_notifications_enabled = models.BooleanField(
        default=False,
        verbose_name="Уведомления в Telegram включены",
        help_text="Включена ли отправка уведомлений о событиях ядра в Telegram.",
    )

    telegram_bot_token = models.TextField(
        blank=True,
        verbose_name="Telegram Bot Token",
        help_text="Токен Telegram-бота, через которого отправляются уведомления.",
    )

    telegram_channel_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Telegram Channel ID",
        help_text="ID канала или чата Telegram, куда отправляются уведомления.",
    )

    class Meta:
        verbose_name = "Глобальные настройки платформы"
        verbose_name_plural = "Глобальные настройки платформы"

    def __str__(self) -> str:
        return "Platform settings"

    @staticmethod
    def _normalize_codes_text(value: str) -> str:
        if not value:
            return ""

        raw_items = value.replace("\n", ",").split(",")
        cleaned_items = []
        seen = set()

        for item in raw_items:
            item = item.strip()
            if not item:
                continue
            if item in seen:
                continue
            seen.add(item)
            cleaned_items.append(item)

        cleaned_items = sorted(cleaned_items, key=lambda x: x.casefold())
        return ", ".join(cleaned_items)

    @staticmethod
    def _split_codes_text(value: str) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def clean(self):
        super().clean()

        qs = self.__class__.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError("В системе может существовать только одна запись PlatformSettings.")

    def save(self, *args, **kwargs):
        self.stablecoin_codes = self._normalize_codes_text(self.stablecoin_codes)
        self.fiat_currency_codes = self._normalize_codes_text(self.fiat_currency_codes)
        self.memo_tag_network_codes = self._normalize_codes_text(self.memo_tag_network_codes)
        super().save(*args, **kwargs)

    def get_stablecoin_codes(self) -> list[str]:
        return self._split_codes_text(self.stablecoin_codes)

    def get_fiat_currency_codes(self) -> list[str]:
        return self._split_codes_text(self.fiat_currency_codes)

    def get_memo_tag_network_codes(self) -> list[str]:
        return self._split_codes_text(self.memo_tag_network_codes)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create()
        return obj
