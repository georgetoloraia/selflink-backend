from django.contrib import admin

from .models import FeatureFlag


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("key", "enabled", "rollout", "updated_at")
    search_fields = ("key", "description")
    list_filter = ("enabled",)
    ordering = ("key",)
