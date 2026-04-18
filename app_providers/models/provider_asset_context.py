from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from app_core.models import UUIDTimestampedModel
from app_providers.models.provider import Provider


AMOUNT_MAX_DIGITS = 30
AMOUNT_DECIMAL_PLACES = 18
PERCENT_MAX_DIGITS = 12
PERCENT_DECIMAL_PLACES = 8
NON_NEGATIVE_DECIMAL = MinValueValidator(Decimal("0"))
PERCENT_MAX_100 = MaxValueValidator(Decimal("100"))


class ProviderAssetContextMatchStatus(models.TextChoices):
    NEW = "NEW", "Новая"
    NORMALIZED = "NORMALIZED", "Нормализована"
    MATCHED_AUTO = "MATCHED_AUTO", "Сопоставлена автоматически"
    MATCHED_MANUAL = "MATCHED_MANUAL", "Сопоставлена вручную"
    AMBIGUOUS = "AMBIGUOUS", "Неоднозначно"
    IGNORED = "IGNORED", "Игнорировать"


class ProviderAssetContext(UUIDTimestampedModel):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="asset_contexts", verbose_name="Провайдер")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Активен", help_text="Используется ли эта запись в системе.")
    asset_code_pl = models.CharField(max_length=64, blank=True, default="", db_index=True, verbose_name="Тикер актива (raw)", help_text="Как код актива пришёл от провайдера.")
    asset_name_pl = models.CharField(max_length=255, blank=True, default="", verbose_name="Название актива (raw)", help_text="Как название актива пришло от провайдера.")
    context_code_pl = models.CharField(max_length=128, blank=True, default="", db_index=True, verbose_name="Код контекста (raw)", help_text="Как код сети/контекста пришёл от провайдера.")
    context_name_pl = models.CharField(max_length=255, blank=True, default="", verbose_name="Название контекста (raw)", help_text="Как название сети/контекста пришло от провайдера.")
    contract_raw = models.CharField(max_length=256, blank=True, null=True, db_index=True, verbose_name="Адрес контракта", help_text="Контракт или иной технический идентификатор, если провайдер его отдаёт.")
    raw_metadata = models.JSONField(default=dict, blank=True, verbose_name="Сырые метаданные", help_text="Дополнительные необработанные данные от провайдера.")
    asset_code = models.CharField(max_length=64, blank=True, default="", db_index=True, verbose_name="Тикер актива", help_text="Нормализованный тикер для поиска и логики.")
    asset_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Название актива", help_text="Нормализованное отображаемое название актива.")
    context_code = models.CharField(max_length=128, blank=True, default="", db_index=True, verbose_name="Код контекста", help_text="Нормализованный код сети/контекста для поиска и логики.")
    context_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Название контекста", help_text="Нормализованное отображаемое название сети/контекста.")
    cluster_no = models.PositiveIntegerField(null=True, blank=True, default=None, db_index=True, verbose_name="Кластер №", help_text="Номер кластера. Проставляется позже автоматически или вручную.")
    is_front = models.BooleanField(default=False, db_index=True, verbose_name="На фронт", help_text="Запись-представитель кластера для фронта. В одном кластере допускается не более одной такой записи.")
    match_status = models.CharField(max_length=32, choices=ProviderAssetContextMatchStatus.choices, default=ProviderAssetContextMatchStatus.NEW, db_index=True, verbose_name="Статус сопоставления")
    D = models.BooleanField(default=True, verbose_name="Ввод (ручной)", help_text="Ручное разрешение или запрет ввода.")
    W = models.BooleanField(default=True, verbose_name="Вывод (ручной)", help_text="Ручное разрешение или запрет вывода.")
    AD = models.BooleanField(default=True, verbose_name="Ввод (авто)", help_text="Автоматический статус ввода, полученный от провайдера.")
    AW = models.BooleanField(default=True, verbose_name="Вывод (авто)", help_text="Автоматический статус вывода, полученный от провайдера.")
    deposit_confirmations = models.PositiveIntegerField(default=0, verbose_name="Подтверждений для ввода", help_text="Сколько подтверждений сети нужно для зачисления депозита.")
    withdraw_confirmations = models.PositiveIntegerField(default=0, verbose_name="Подтверждений для вывода", help_text="Если провайдер отдаёт такое значение отдельно, храним его здесь.")
    deposit_fee_fixed = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("0"), verbose_name="Фикс. комиссия на ввод", help_text="Комиссия в единицах самого актива. Может быть отрицательной.")
    deposit_fee_percent = models.DecimalField(max_digits=PERCENT_MAX_DIGITS, decimal_places=PERCENT_DECIMAL_PLACES, default=Decimal("0"), validators=[PERCENT_MAX_100], verbose_name="Комиссия на ввод, %", help_text="Процентная комиссия. Может быть отрицательной, но не может быть больше 100%.")
    deposit_fee_min_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("0"), verbose_name="Мин. комиссия на ввод", help_text="Минимальная комиссия на ввод в единицах актива. Может быть отрицательной.")
    deposit_fee_max_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, null=True, blank=True, verbose_name="Макс. комиссия на ввод", help_text="Максимальная комиссия на ввод в единицах актива. Если лимита нет, поле остаётся пустым.")
    withdraw_fee_fixed = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("0"), verbose_name="Фикс. комиссия на вывод", help_text="Комиссия в единицах самого актива. Может быть отрицательной.")
    withdraw_fee_percent = models.DecimalField(max_digits=PERCENT_MAX_DIGITS, decimal_places=PERCENT_DECIMAL_PLACES, default=Decimal("0"), validators=[PERCENT_MAX_100], verbose_name="Комиссия на вывод, %", help_text="Процентная комиссия. Может быть отрицательной, но не может быть больше 100%.")
    withdraw_fee_min_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("0"), verbose_name="Мин. комиссия на вывод", help_text="Минимальная комиссия на вывод в единицах актива. Может быть отрицательной.")
    withdraw_fee_max_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, null=True, blank=True, verbose_name="Макс. комиссия на вывод", help_text="Максимальная комиссия на вывод в единицах актива. Если лимита нет, поле остаётся пустым.")
    deposit_min_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, null=True, blank=True, validators=[NON_NEGATIVE_DECIMAL], verbose_name="Мин. сумма ввода", help_text="Минимальная сумма ввода в единицах актива.")
    deposit_max_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, null=True, blank=True, validators=[NON_NEGATIVE_DECIMAL], verbose_name="Макс. сумма ввода", help_text="Максимальная сумма ввода в единицах актива, если провайдер её отдаёт.")
    withdraw_min_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, null=True, blank=True, validators=[NON_NEGATIVE_DECIMAL], verbose_name="Мин. сумма вывода", help_text="Минимальная сумма вывода в единицах актива.")
    withdraw_max_amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, null=True, blank=True, validators=[NON_NEGATIVE_DECIMAL], verbose_name="Макс. сумма вывода", help_text="Максимальная сумма вывода в единицах актива, если провайдер её отдаёт.")
    min_trade_amount_usdt = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("5"), validators=[NON_NEGATIVE_DECIMAL], verbose_name="Мин. торговый объём, USDT", help_text="Минимальный торговый объём / минимальный лот в эквиваленте USDT.")
    trades_enabled = models.BooleanField(default=False, db_index=True, verbose_name="Торговля разрешена", help_text="Можно ли торговать этим активом у провайдера на спотовом рынке.")
    is_stablecoin = models.BooleanField(default=False, db_index=True, verbose_name="Стейблкоин")
    amount_precision = models.PositiveSmallIntegerField(default=8, verbose_name="Точность актива", help_text="Сколько знаков после запятой допустимо для этого инструмента.")
    nominal = models.PositiveIntegerField(default=1, verbose_name="Номинал", help_text="Номинал инструмента. Для большинства активов = 1.")
    reserve_current = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("0"), validators=[NON_NEGATIVE_DECIMAL], verbose_name="Текущий резерв", help_text="Текущий доступный резерв у провайдера по этой записи.")
    reserve_min = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("0"), validators=[NON_NEGATIVE_DECIMAL], verbose_name="Мин. резерв", help_text="Минимальный допустимый резерв для логики маршрутизации.")
    reserve_max = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES, default=Decimal("0"), validators=[NON_NEGATIVE_DECIMAL], verbose_name="Макс. резерв", help_text="Максимальный допустимый резерв, если вы это используете в своей логике.")
    icon_file = models.ImageField(upload_to="provider_asset_context_icons/", blank=True, null=True, verbose_name="Иконка (файл)")
    icon_url = models.URLField(blank=True, default="", verbose_name="Иконка (URL)", help_text="Иконка, которую отдал провайдер или которую вы указали вручную.")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "AssetContext провайдера"
        verbose_name_plural = "04 AssetContext провайдеров"
        ordering = ("provider", "cluster_no", "asset_code", "context_code", "id")
        indexes = [models.Index(fields=["provider", "is_active"]), models.Index(fields=["provider", "asset_code", "context_code"]), models.Index(fields=["contract_raw"])]
        constraints = [models.UniqueConstraint(fields=["cluster_no"], condition=Q(is_front=True, cluster_no__isnull=False), name="uniq_front_provider_asset_context_per_cluster")]

    def __str__(self) -> str:
        base = f"{self.provider.code} | {self.asset_code or self.asset_code_pl or '—'} | {self.context_code or self.context_code_pl or '—'}"
        if self.cluster_no:
            return f"{base} | cluster={self.cluster_no}"
        return base

    @property
    def deposit_enabled(self) -> bool:
        return self.D and self.AD

    @property
    def withdraw_enabled(self) -> bool:
        return self.W and self.AW

    def save(self, *args, **kwargs):
        self.asset_code_pl = (self.asset_code_pl or "").strip()
        self.asset_name_pl = (self.asset_name_pl or "").strip()
        self.context_code_pl = (self.context_code_pl or "").strip()
        self.context_name_pl = (self.context_name_pl or "").strip()
        self.asset_code = ((self.asset_code_pl or self.asset_code or "").strip()).upper()
        self.context_code = ((self.context_code_pl or self.context_code or "").strip()).upper()
        self.asset_name = (self.asset_name or self.asset_name_pl or "").strip()
        self.context_name = (self.context_name or self.context_name_pl or "").strip()
        if self.contract_raw:
            self.contract_raw = self.contract_raw.strip()
        if self.description:
            self.description = self.description.strip()
        super().save(*args, **kwargs)
