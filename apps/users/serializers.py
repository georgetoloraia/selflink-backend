from __future__ import annotations

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
        fields = ["privacy", "dm_policy", "language", "quiet_hours"]


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

    class Meta:
        model = User
        fields = ["email", "handle", "name", "password"]

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        UserSettings.objects.get_or_create(user=user)
        return user


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
