from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.audit.views import AuditEventViewSet

router = DefaultRouter()
router.register(r"audit/events", AuditEventViewSet, basename="audit-events")

urlpatterns = [
    path("", include(router.urls)),
]
