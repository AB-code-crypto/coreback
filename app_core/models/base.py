from django.db import models
import uuid


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлено"
    )

    class Meta:
        abstract = True


class UUIDPrimaryKeyModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )

    class Meta:
        abstract = True


class UUIDTimestampedModel(UUIDPrimaryKeyModel, TimestampedModel):
    class Meta:
        abstract = True
