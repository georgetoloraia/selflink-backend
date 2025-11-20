from __future__ import annotations

from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class BirthData(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="birth_data",
    )
    date_of_birth = models.DateField()
    time_of_birth = models.TimeField()
    timezone = models.CharField(max_length=64)
    city = models.CharField(max_length=128, blank=True)
    country = models.CharField(max_length=128, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def clean(self) -> None:
        errors: dict[str, ValidationError] = {}
        if not -90 <= self.latitude <= 90:
            errors["latitude"] = ValidationError("Latitude must be between -90 and 90.")
        if not -180 <= self.longitude <= 180:
            errors["longitude"] = ValidationError("Longitude must be between -180 and 180.")
        try:
            ZoneInfo(self.timezone)
        except Exception:
            errors["timezone"] = ValidationError("Timezone must be a valid IANA string.")
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"BirthData<{self.user_id}>"


class NatalChart(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="natal_chart",
    )
    birth_data = models.OneToOneField(
        BirthData,
        on_delete=models.CASCADE,
        related_name="natal_chart",
    )
    planets = models.JSONField()
    houses = models.JSONField()
    aspects = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"NatalChart<{self.user_id}>"
