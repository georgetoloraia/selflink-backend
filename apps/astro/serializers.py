from __future__ import annotations

from zoneinfo import ZoneInfo

from rest_framework import serializers

from apps.astro.models import BirthData, NatalChart


class BirthDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirthData
        fields = [
            "date_of_birth",
            "time_of_birth",
            "timezone",
            "city",
            "country",
            "latitude",
            "longitude",
        ]
        extra_kwargs = {
            "date_of_birth": {"required": False},
            "time_of_birth": {"required": False},
            "timezone": {"required": False, "allow_blank": True},
            "latitude": {"required": False},
            "longitude": {"required": False},
            "city": {"required": False, "allow_blank": True},
            "country": {"required": False, "allow_blank": True},
        }

    def validate_timezone(self, value: str) -> str:
        if not value:
            return value
        try:
            ZoneInfo(value)
        except Exception:
            raise serializers.ValidationError("Invalid timezone. Use a valid IANA timezone string.")
        return value

    def validate_latitude(self, value: float) -> float:
        if value is None:
            return value
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value: float) -> float:
        if value is None:
            return value
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data: dict) -> BirthData:
        user = self.context["request"].user
        profile = getattr(user, "profile", None)
        personal_map = getattr(user, "personal_map", None)

        date_of_birth = (
            validated_data.get("date_of_birth")
            or getattr(profile, "birth_date", None)
            or getattr(personal_map, "birth_date", None)
            or getattr(user, "birth_date", None)
        )
        time_of_birth = (
            validated_data.get("time_of_birth")
            or getattr(profile, "birth_time", None)
            or getattr(personal_map, "birth_time", None)
            or getattr(user, "birth_time", None)
        )
        if not date_of_birth or time_of_birth is None:
            raise serializers.ValidationError(
                {"detail": "Birth date and time are not set. Please complete your Personal Map."}
            )

        city = (
            validated_data.get("city")
            or getattr(profile, "birth_city", None)
            or getattr(personal_map, "birth_place_city", None)
            or ""
        )
        country = (
            validated_data.get("country")
            or getattr(profile, "birth_country", None)
            or getattr(personal_map, "birth_place_country", None)
            or ""
        )
        timezone = validated_data.get("timezone") or getattr(profile, "birth_timezone", "") or ""
        latitude = (
            validated_data.get("latitude")
            if validated_data.get("latitude") is not None
            else getattr(profile, "birth_latitude", None)
        )
        longitude = (
            validated_data.get("longitude")
            if validated_data.get("longitude") is not None
            else getattr(profile, "birth_longitude", None)
        )

        instance, _ = BirthData.objects.update_or_create(
            user=user,
            defaults={
                "date_of_birth": date_of_birth,
                "time_of_birth": time_of_birth,
                "timezone": timezone,
                "city": city,
                "country": country,
                "latitude": latitude,
                "longitude": longitude,
            },
        )
        return instance

    def update(self, instance: BirthData, validated_data: dict) -> BirthData:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data.keys()))
        return instance


class NatalChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = NatalChart
        fields = ["planets", "houses", "aspects", "calculated_at"]
