from __future__ import annotations

from rest_framework import serializers

from .models import MediaAsset


class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "s3_key",
            "mime",
            "width",
            "height",
            "duration",
            "status",
            "checksum",
            "meta",
            "created_at",
        ]
        read_only_fields = ["status", "checksum", "created_at"]
