from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class SoulMatchProfile(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="soulmatch_profile")
    sun = models.CharField(max_length=32, blank=True)
    moon = models.CharField(max_length=32, blank=True)
    life_path = models.CharField(max_length=32, blank=True)
    avg_sentiment = models.FloatField(default=0.0)
    social_score = models.FloatField(default=0.0)
    traits = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "SoulMatch Profile"
        verbose_name_plural = "SoulMatch Profiles"


class SoulMatchScore(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="soulmatches")
    target = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="matched_by")
    score = models.FloatField()
    breakdown = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "target")
        verbose_name = "SoulMatch Score"
        verbose_name_plural = "SoulMatch Scores"
