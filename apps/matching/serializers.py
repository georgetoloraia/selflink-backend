from __future__ import annotations

from rest_framework import serializers

from apps.users.models import User


class SoulmatchUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "handle", "name", "photo"]


class SoulmatchResultSerializer(serializers.Serializer):
    user = SoulmatchUserSerializer()
    score = serializers.IntegerField()
    components = serializers.DictField()
    tags = serializers.ListField(child=serializers.CharField())
    lens = serializers.CharField(required=False)
    lens_label = serializers.CharField(required=False)
    lens_reason_short = serializers.CharField(required=False)
    timing_score = serializers.IntegerField(required=False)
    timing_window = serializers.DictField(required=False, allow_null=True)
    timing_summary = serializers.CharField(required=False)
    compatibility_trend = serializers.CharField(required=False)
    explanation_level = serializers.CharField(required=False)
    explanation = serializers.DictField(required=False)
