from __future__ import annotations

from rest_framework import permissions, viewsets

from .models import Enforcement, Report
from .permissions import IsModerationStaff
from .serializers import AdminReportSerializer, EnforcementSerializer, ReportSerializer


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        return Report.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer: ReportSerializer) -> None:  # type: ignore[override]
        serializer.save()


class EnforcementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnforcementSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Enforcement.objects.all().order_by("-created_at")


class AdminReportViewSet(viewsets.ModelViewSet):
    serializer_class = AdminReportSerializer
    permission_classes = [IsModerationStaff]
    queryset = Report.objects.select_related("reporter").order_by("-created_at")
