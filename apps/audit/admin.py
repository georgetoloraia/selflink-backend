from __future__ import annotations

from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "object_type", "object_id", "actor_user", "actor_ip")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "actor_user__email", "actor_user__handle")
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False
