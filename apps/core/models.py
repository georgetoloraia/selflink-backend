from __future__ import annotations

from django.db import models

from libs.idgen import generate_id


class SnowflakePrimaryKeyModel(models.Model):
    id = models.BigIntegerField(primary_key=True, default=generate_id, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(SnowflakePrimaryKeyModel, TimeStampedModel):
    class Meta:
        abstract = True
