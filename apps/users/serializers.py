from __future__ import annotations

import re
from secrets import token_hex

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Device, User, UserSettings


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id", "device_type", "push_token", "last_seen", "created_at"]
        read_only_fields = ["id", "last_seen", "created_at"]


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            "privacy",
            "dm_policy",
            "language",
            "quiet_hours",
            "push_enabled",
            "email_enabled",
            "digest_enabled",
        ]


class UserSerializer(serializers.ModelSerializer):
    settings = UserSettingsSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "handle",
            "name",
            "bio",
            "photo",
            "birth_date",
            "birth_time",
            "birth_place",
            "locale",
            "flags",
            "created_at",
            "updated_at",
            "settings",
        ]
        read_only_fields = ["email", "created_at", "updated_at", "flags"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    fullName = serializers.CharField(write_only=True, required=False, allow_blank=True)
    intention = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["email", "handle", "name", "password", "fullName", "intention"]
        extra_kwargs = {
            "handle": {"required": False, "allow_blank": True},
            "name": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        max_length = User._meta.get_field("handle").max_length

        full_name = (attrs.pop("fullName", "") or "").strip()
        incoming_name = (attrs.get("name") or "").strip()
        if full_name and not incoming_name:
            attrs["name"] = full_name
        elif incoming_name:
            attrs["name"] = incoming_name

        if not attrs.get("name"):
            raise serializers.ValidationError({"fullName": "Please provide your full name."})

        handle = (attrs.get("handle") or "").strip()
        if handle:
            normalized = _normalize_handle(handle, max_length)
            if not normalized:
                raise serializers.ValidationError({"handle": "Handle must contain letters or numbers."})
            if User.objects.filter(handle=normalized).exists():
                raise serializers.ValidationError({"handle": "Handle is already taken."})
            attrs["handle"] = normalized
        else:
            attrs["handle"] = _generate_unique_handle(attrs["name"], attrs["email"], max_length)

        # The frontend sends intention for contextual onboarding; we simply drop it for now.
        attrs.pop("intention", None)
        return attrs

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        UserSettings.objects.get_or_create(user=user)
        return user


def _normalize_handle(value: str, max_length: int) -> str:
    cleaned = re.sub(r"[^a-z0-9_]", "", value.lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_length]


def _generate_unique_handle(name: str, email: str, max_length: int) -> str:
    candidates = [name, email.split("@", 1)[0], "selflink"]
    for candidate in candidates:
        normalized = _normalize_handle(candidate or "", max_length)
        if normalized and not User.objects.filter(handle=normalized).exists():
            return normalized

    base = _normalize_handle(name or "selflink", max_length) or "selflink"
    suffix_length = 4
    while True:
        suffix = token_hex(suffix_length // 2)
        trim_length = max_length - len(suffix)
        prefix = base[:trim_length] if trim_length > 0 else ""
        candidate = f"{prefix}{suffix}"
        if not User.objects.filter(handle=candidate).exists():
            return candidate


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email")
        password = attrs.get("password")
        user = authenticate(request=self.context.get("request"), email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    settings = UserSettingsSerializer()

    class Meta:
        model = User
        fields = [
            "name",
            "bio",
            "photo",
            "birth_date",
            "birth_time",
            "birth_place",
            "locale",
            "settings",
        ]

    def update(self, instance: User, validated_data: dict) -> User:
        settings_data = validated_data.pop("settings", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if settings_data:
            settings, _ = UserSettings.objects.get_or_create(user=instance)
            for attr, value in settings_data.items():
                setattr(settings, attr, value)
            settings.save()
        return instance
