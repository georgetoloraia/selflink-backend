from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel

GENDER_CHOICES = (
    ("male", "male"),
    ("female", "female"),
    ("non_binary", "non_binary"),
    ("other", "other"),
    ("prefer_not_to_say", "prefer_not_to_say"),
)

ORIENTATION_CHOICES = (
    ("hetero", "hetero"),
    ("homo", "homo"),
    ("bi", "bi"),
    ("pan", "pan"),
    ("asexual", "asexual"),
    ("other", "other"),
    ("prefer_not_to_say", "prefer_not_to_say"),
)

REL_GOAL_CHOICES = (
    ("casual", "casual"),
    ("long_term", "long_term"),
    ("marriage", "marriage"),
    ("unsure", "unsure"),
)

ATTACHMENT_CHOICES = (
    ("secure", "secure"),
    ("anxious", "anxious"),
    ("avoidant", "avoidant"),
    ("mixed", "mixed"),
)


class UserProfile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    gender = models.CharField(max_length=32, choices=GENDER_CHOICES, blank=True)
    orientation = models.CharField(max_length=32, choices=ORIENTATION_CHOICES, blank=True)
    relationship_goal = models.CharField(max_length=32, choices=REL_GOAL_CHOICES, default="unsure")
    values = models.JSONField(default=list, blank=True)
    preferred_lifestyle = models.JSONField(default=list, blank=True)
    attachment_style = models.CharField(max_length=32, choices=ATTACHMENT_CHOICES, blank=True)
    love_language = models.JSONField(default=list, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def clean(self) -> None:
        errors: dict[str, ValidationError] = {}
        for field_name in ["values", "preferred_lifestyle", "love_language"]:
            field_value = getattr(self, field_name)
            if field_value is None:
                continue
            if not isinstance(field_value, list) or not all(isinstance(v, str) for v in field_value):
                errors[field_name] = ValidationError("Must be a list of strings.")
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"UserProfile<{self.user_id}>"
