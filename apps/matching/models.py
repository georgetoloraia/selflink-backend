from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class SoulMatchResult(BaseModel):
    pair_key = models.CharField(max_length=64)
    rules_version = models.CharField(max_length=32, default="v1")
    score = models.FloatField()
    payload_json = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("pair_key", "rules_version")
        indexes = [
            models.Index(fields=["pair_key", "rules_version"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"SoulMatchResult<{self.pair_key}:{self.rules_version}>"

