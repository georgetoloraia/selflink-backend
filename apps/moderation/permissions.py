from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsModerationStaff(BasePermission):
    def has_permission(self, request, view):  # type: ignore[override]
        user = request.user
        if not user or user.is_anonymous:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return user.groups.filter(name="moderation_team").exists()
