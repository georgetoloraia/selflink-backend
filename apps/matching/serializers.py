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
