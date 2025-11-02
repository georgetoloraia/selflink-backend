from __future__ import annotations

from rest_framework import permissions, viewsets

from .models import MediaAsset
from .serializers import MediaAssetSerializer


class MediaAssetViewSet(viewsets.ModelViewSet):
    serializer_class = MediaAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        return MediaAsset.objects.filter(owner=self.request.user)

    def perform_create(self, serializer: MediaAssetSerializer) -> None:  # type: ignore[override]
        serializer.save(owner=self.request.user)
