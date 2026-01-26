from __future__ import annotations

from django import forms
from django.contrib import admin

from apps.payments.models import GiftType, PaymentCheckout, PaymentEvent, Plan, Subscription, Wallet


class GiftTypeAdminForm(forms.ModelForm):
    media_url = forms.CharField(required=False)
    animation_url = forms.CharField(required=False)
    art_url = forms.CharField(required=False)

    class Meta:
        model = GiftType
        fields = "__all__"


@admin.register(GiftType)
class GiftTypeAdmin(admin.ModelAdmin):
    form = GiftTypeAdminForm
    list_display = ("id", "key", "name", "kind", "price_slc_cents", "is_active", "created_at")
    list_filter = ("kind", "is_active")
    search_fields = ("key", "name")
    ordering = ("price_slc_cents", "name")
    fields = (
        "key",
        "name",
        "price_cents",
        "price_slc_cents",
        "kind",
        "media_file",
        "media_url",
        "animation_file",
        "animation_url",
        "art_url",
        "is_active",
        "effects",
        "metadata",
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price_cents", "interval", "is_active")
    list_filter = ("interval", "is_active")
    search_fields = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "status", "current_period_end")
    list_filter = ("status",)
    search_fields = ("user__email", "user__handle")
    readonly_fields = ("user", "plan", "status", "current_period_start", "current_period_end", "created_at", "updated_at")

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "balance_cents", "external_customer_id", "created_at")
    search_fields = ("user__email", "user__handle", "external_customer_id")
    readonly_fields = ("user", "balance_cents", "external_customer_id", "created_at", "updated_at")

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "provider_event_id", "user", "amount_cents", "currency", "status", "verified_at")
    list_filter = ("provider", "status", "currency")
    search_fields = ("provider_event_id", "user__email", "user__handle")
    readonly_fields = (
        "provider",
        "provider_event_id",
        "event_type",
        "user",
        "amount_cents",
        "currency",
        "status",
        "minted_coin_event",
        "raw_body_hash",
        "verified_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False


@admin.register(PaymentCheckout)
class PaymentCheckoutAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "reference", "user", "amount_cents", "currency", "status", "created_at")
    list_filter = ("provider", "status", "currency")
    search_fields = ("reference", "provider_reference", "user__email", "user__handle")
    readonly_fields = (
        "provider",
        "reference",
        "provider_reference",
        "user",
        "amount_cents",
        "currency",
        "status",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None):  # type: ignore[override]
        return False

    def has_delete_permission(self, request, obj=None):  # type: ignore[override]
        return False
