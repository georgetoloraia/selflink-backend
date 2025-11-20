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

    def validate_timezone(self, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception:
            raise serializers.ValidationError("Invalid timezone. Use a valid IANA timezone string.")
        return value

    def validate_latitude(self, value: float) -> float:
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value: float) -> float:
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data: dict) -> BirthData:
        user = self.context["request"].user
        instance, _ = BirthData.objects.update_or_create(
            user=user,
            defaults=validated_data,
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
