from __future__ import annotations

from rest_framework import serializers

from .models import AstroProfile, MatrixData
from .services import compute_life_path


class AstroProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AstroProfile
        fields = [
            "id",
            "sun",
            "moon",
            "ascendant",
            "planets",
            "aspects",
            "houses",
            "raw_payload",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "raw_payload", "created_at", "updated_at"]


class MatrixDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatrixData
        fields = ["id", "life_path", "traits", "raw_payload", "created_at", "updated_at"]
        read_only_fields = ["id", "raw_payload", "created_at", "updated_at"]


class MatrixSyncSerializer(serializers.Serializer):
    sun = serializers.CharField(required=False)
    moon = serializers.CharField(required=False)
    ascendant = serializers.CharField(required=False)
    planets = serializers.JSONField(required=False)
    aspects = serializers.JSONField(required=False)
    houses = serializers.JSONField(required=False)

    def save(self) -> MatrixData:
        user = self.context["request"].user
        astro, _ = AstroProfile.objects.get_or_create(user=user)
        matrix, _ = MatrixData.objects.get_or_create(user=user)
        fields = ["sun", "moon", "ascendant", "planets", "aspects", "houses"]
        for field in fields:
            value = self.validated_data.get(field)
            if value is not None:
                setattr(astro, field, value)
        astro.raw_payload = self.validated_data
        astro.save()

        life_path, traits = compute_life_path(user.birth_date)
        matrix.life_path = life_path
        matrix.traits = traits
        matrix.raw_payload = {"source": "sync", "astro": self.validated_data}
        matrix.save()
        return matrix
