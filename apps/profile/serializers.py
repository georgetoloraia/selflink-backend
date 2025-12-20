from __future__ import annotations

from rest_framework import serializers

from apps.profile.models import UserProfile


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
            "birth_date",
            "birth_time",
            "birth_city",
            "birth_country",
            "birth_timezone",
            "birth_latitude",
            "birth_longitude",
        ]
        extra_kwargs = {
            "birth_timezone": {"required": False, "allow_blank": True},
            "birth_latitude": {"required": False},
            "birth_longitude": {"required": False},
            "birth_date": {"required": False},
            "birth_time": {"required": False},
            "birth_city": {"required": False, "allow_blank": True},
            "birth_country": {"required": False, "allow_blank": True},
        }

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
