from __future__ import annotations

from django.contrib import admin

from apps.users.models import UserPII


@admin.register(UserPII)
class UserPIIAdmin(admin.ModelAdmin):
    list_display = ("user_id", "email", "full_name", "updated_at")
    search_fields = ("user__email", "user__handle", "email", "full_name")
    readonly_fields = ("created_at", "updated_at")

    def has_view_permission(self, request, obj=None) -> bool:  # type: ignore[override]
        return request.user.is_superuser or request.user.has_perm("users.view_userpii")

    def has_add_permission(self, request) -> bool:  # type: ignore[override]
        return request.user.is_superuser or request.user.has_perm("users.add_userpii")

    def has_change_permission(self, request, obj=None) -> bool:  # type: ignore[override]
        return request.user.is_superuser or request.user.has_perm("users.change_userpii")

    def has_delete_permission(self, request, obj=None) -> bool:  # type: ignore[override]
        return request.user.is_superuser or request.user.has_perm("users.delete_userpii")

