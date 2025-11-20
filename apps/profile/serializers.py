from __future__ import annotations

from rest_framework import serializers

from apps.profile.models import (
    ATTACHMENT_CHOICES,
    GENDER_CHOICES,
    ORIENTATION_CHOICES,
    REL_GOAL_CHOICES,
    UserProfile,
)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "gender",
            "orientation",
            "relationship_goal",
            "values",
            "preferred_lifestyle",
            "attachment_style",
            "love_language",
        ]

    def validate_values(self, value):
        return self._validate_list(value, "values")

    def validate_preferred_lifestyle(self, value):
        return self._validate_list(value, "preferred_lifestyle")

    def validate_love_language(self, value):
        return self._validate_list(value, "love_language")

    def _validate_list(self, value, field_name):
        if value in (None, []):
            return value or []
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise serializers.ValidationError(f"{field_name} must be a list of strings.")
        if len(value) > 32:
            raise serializers.ValidationError(f"{field_name} must contain 32 items or fewer.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        profile, _ = UserProfile.objects.update_or_create(
            user=user,
            defaults=validated_data,
        )
        return profile

    def update(self, instance: UserProfile, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data.keys()))
        return instance
