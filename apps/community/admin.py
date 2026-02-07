from __future__ import annotations

from django.contrib import admin

from .models import (
    AgreementAcceptance,
    ArtifactComment,
    Problem,
    ProblemAgreement,
    ProblemComment,
    ProblemWork,
    WorkArtifact,
)


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("id", "title")
    ordering = ("-created_at", "-id")


@admin.register(ProblemAgreement)
class ProblemAgreementAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("id", "problem__title")
    ordering = ("-created_at", "-id")


@admin.register(AgreementAcceptance)
class AgreementAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "agreement", "user", "accepted_at")
    search_fields = ("id", "user__email", "user__handle", "problem__title")
    ordering = ("-accepted_at", "-id")


@admin.register(ProblemWork)
class ProblemWorkAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "user__email", "user__handle", "problem__title")
    ordering = ("-created_at", "-id")


@admin.register(WorkArtifact)
class WorkArtifactAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "user", "title", "created_at")
    search_fields = ("id", "title", "user__email", "user__handle", "problem__title")
    ordering = ("-created_at", "-id")


@admin.register(ProblemComment)
class ProblemCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "user", "created_at")
    search_fields = ("id", "user__email", "user__handle", "problem__title")
    ordering = ("-created_at", "-id")


@admin.register(ArtifactComment)
class ArtifactCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "artifact", "user", "created_at")
    search_fields = ("id", "user__email", "user__handle", "artifact__title")
    ordering = ("-created_at", "-id")
