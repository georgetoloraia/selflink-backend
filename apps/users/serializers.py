from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.social.models import Follow

from .models import Device, PersonalMapProfile, User, UserSettings
from .utils import generate_unique_handle, normalize_handle


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
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

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
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
            "created_at",
            "updated_at",
            "settings",
        ]
        read_only_fields = ["email", "created_at", "updated_at", "flags"]

    def _get_count_from_attr(self, obj: User, attr_name: str, related_name: str) -> int:
        value = getattr(obj, attr_name, None)
        if value is not None:
            return int(value)
        related_manager = getattr(obj, related_name, None)
        if related_manager is None:
            return 0
        return related_manager.count()

    def get_followers_count(self, obj: User) -> int:
        return self._get_count_from_attr(obj, "followers_count", "followers")

    def get_following_count(self, obj: User) -> int:
        return self._get_count_from_attr(obj, "following_count", "following")

    def get_posts_count(self, obj: User) -> int:
        return self._get_count_from_attr(obj, "posts_count", "posts")

    def get_is_following(self, obj: User) -> bool:
        annotated_value = getattr(obj, "is_following", None)
        if annotated_value is not None:
            return bool(annotated_value)
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        if request.user == obj:
            return False
        return Follow.objects.filter(follower=request.user, followee=obj).exists()


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
            normalized = normalize_handle(handle, max_length)
            if not normalized:
                raise serializers.ValidationError({"handle": "Handle must contain letters or numbers."})
            if User.objects.filter(handle=normalized).exists():
                raise serializers.ValidationError({"handle": "Handle is already taken."})
            attrs["handle"] = normalized
        else:
            attrs["handle"] = generate_unique_handle(attrs["name"], attrs["email"], max_length)

        # The frontend sends intention for contextual onboarding; we simply drop it for now.
        attrs.pop("intention", None)
        return attrs

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


class PersonalMapProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    is_complete = serializers.SerializerMethodField()
    birth_date = serializers.DateField(input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    birth_time = serializers.TimeField(
        required=False,
        allow_null=True,
        input_formats=["%H:%M", "%H:%M:%S"],
    )
    avatar_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = PersonalMapProfile
        fields = [
            "email",
            "first_name",
            "last_name",
            "birth_date",
            "birth_time",
            "birth_place_country",
            "birth_place_city",
            "avatar_image",
            "is_complete",
        ]
        read_only_fields = ["email", "is_complete"]

    def create(self, validated_data: dict) -> PersonalMapProfile:
        user = self.context["request"].user
        profile = PersonalMapProfile.objects.create(user=user, **validated_data)
        self._sync_user_fields(user, profile)
        return profile

    def update(self, instance: PersonalMapProfile, validated_data: dict) -> PersonalMapProfile:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._sync_user_fields(instance.user, instance)
        return instance

    def get_is_complete(self, obj: PersonalMapProfile) -> bool:
        required = [
            obj.first_name,
            obj.last_name,
            obj.birth_date,
            obj.birth_place_country,
            obj.birth_place_city,
        ]
        return all(required)

    def _sync_user_fields(self, user: User, profile: PersonalMapProfile) -> None:
        update_fields: list[str] = []
        full_name = " ".join(part for part in [profile.first_name, profile.last_name] if part).strip()
        if full_name and user.name != full_name:
            user.name = full_name
            update_fields.append("name")

        if profile.birth_date and user.birth_date != profile.birth_date:
            user.birth_date = profile.birth_date
            update_fields.append("birth_date")

        if profile.birth_time != user.birth_time:
            user.birth_time = profile.birth_time
            update_fields.append("birth_time")

        place_parts = [part for part in [profile.birth_place_city, profile.birth_place_country] if part]
        place = ", ".join(place_parts)
        if place and user.birth_place != place:
            user.birth_place = place
            update_fields.append("birth_place")

        if profile.avatar_image and profile.avatar_image.url:
            photo_url = profile.avatar_image.url
            if user.photo != photo_url:
                user.photo = photo_url
                update_fields.append("photo")

        if update_fields:
            user.save(update_fields=update_fields)
