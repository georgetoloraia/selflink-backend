from __future__ import annotations

from rest_framework import permissions, viewsets

from apps.audit.models import AuditEvent
from apps.audit.serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = AuditEvent.objects.select_related("actor_user").order_by("-created_at", "-id")
