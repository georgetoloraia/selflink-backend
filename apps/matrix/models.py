from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class AstroProfile(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="astro_profile")
    sun = models.CharField(max_length=32, blank=True)
    moon = models.CharField(max_length=32, blank=True)
    ascendant = models.CharField(max_length=32, blank=True)
    planets = models.JSONField(default=dict, blank=True)
    aspects = models.JSONField(default=dict, blank=True)
    houses = models.JSONField(default=dict, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)


class MatrixData(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="matrix_data")
    life_path = models.CharField(max_length=32, blank=True)
    traits = models.JSONField(default=dict, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
