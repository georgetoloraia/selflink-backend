from __future__ import annotations

from django.contrib import admin

from apps.coin.models import CoinAccount, CoinEvent, CoinLedgerEntry, MonthlyCoinSnapshot


@admin.register(CoinAccount)
class CoinAccountAdmin(admin.ModelAdmin):
    list_display = ("account_key", "user", "is_system", "status", "created_at")
    search_fields = ("account_key", "user__email", "user__handle")
    readonly_fields = ("account_key", "user", "is_system", "status", "created_at", "updated_at")

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(CoinEvent)
class CoinEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "created_by", "occurred_at", "idempotency_key", "ruleset_version")
    list_filter = ("event_type",)
    search_fields = ("idempotency_key", "created_by__email", "created_by__handle")
    readonly_fields = (
        "event_type",
        "occurred_at",
        "created_by",
        "idempotency_key",
        "metadata",
        "note",
        "ruleset_version",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(CoinLedgerEntry)
class CoinLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "tx_id", "event", "account_key", "direction", "amount_cents", "currency", "created_at")
    list_filter = ("direction", "currency")
    search_fields = ("account_key", "tx_id")
    readonly_fields = (
        "tx_id",
        "event",
        "account_key",
        "direction",
        "amount_cents",
        "currency",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(MonthlyCoinSnapshot)
class MonthlyCoinSnapshotAdmin(admin.ModelAdmin):
    list_display = ("period", "total_events", "total_entries", "total_volume_cents", "ledger_hash")
    readonly_fields = ("period", "total_events", "total_entries", "total_volume_cents", "ledger_hash", "created_at", "updated_at")

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False
