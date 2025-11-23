from django.contrib import admin

from .models import MentorMessage, MentorSession


@admin.register(MentorSession)
class MentorSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "language", "active", "started_at")
    list_filter = ("mode", "language", "active", "started_at")
    search_fields = ("user__email", "user__id")
    # autocomplete_fields = ("user",)


@admin.register(MentorMessage)
class MentorMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "session__id", "session__user__email")
    # autocomplete_fields = ("session",)

    def short_content(self, obj):
        return (obj.content[:80] + "…") if len(obj.content) > 80 else obj.content

    short_content.short_description = "content"
