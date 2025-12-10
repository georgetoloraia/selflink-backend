from __future__ import annotations

from django.contrib import admin

from apps.contrib_rewards.models import ContributorProfile, MonthlyRewardSnapshot, Payout, RewardEvent


@admin.register(ContributorProfile)
class ContributorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "github_username", "created_at")
    search_fields = ("user__email", "user__handle", "github_username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RewardEvent)
class RewardEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "contributor", "points", "occurred_at", "reference")
    list_filter = ("event_type",)
    search_fields = ("reference", "contributor__user__email", "contributor__github_username")
    readonly_fields = ("contributor", "event_type", "points", "occurred_at", "reference", "metadata", "notes", "created_at", "updated_at")

    def has_add_permission(self, request):  # type: ignore[override]
        return True

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(MonthlyRewardSnapshot)
class MonthlyRewardSnapshotAdmin(admin.ModelAdmin):
    list_display = ("period", "contributor_pool_cents", "total_points", "total_events", "ledger_hash")
    readonly_fields = ("period", "contributor_pool_cents", "total_points", "total_events", "ledger_hash", "dispute_window_ends_at", "created_at", "updated_at")

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("snapshot", "contributor", "amount_cents", "status")
    list_filter = ("status",)
    search_fields = ("contributor__user__email", "contributor__github_username")
    readonly_fields = ("snapshot", "contributor", "points", "amount_cents", "metadata", "created_at", "updated_at")

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        # Status transitions should be handled through dedicated flows.
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False
