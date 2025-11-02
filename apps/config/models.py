from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class FeatureFlag(BaseModel):
    key = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=255, blank=True)
    enabled = models.BooleanField(default=False)
    rollout = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.key} ({'on' if self.enabled else 'off'})"

    def save(self, *args, **kwargs):  # type: ignore[override]
        super().save(*args, **kwargs)
        from .services import invalidate_cache

        invalidate_cache(self.key)

    def delete(self, *args, **kwargs):  # type: ignore[override]
        key = self.key
        super().delete(*args, **kwargs)
        from .services import invalidate_cache

        invalidate_cache(key)
