from __future__ import annotations

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from apps.payments.models import GiftType, PaymentCheckout, PaymentEvent, Plan, Subscription, Wallet


class GiftTypeAdminForm(forms.ModelForm):
    media_url = forms.CharField(required=False)
    animation_url = forms.CharField(required=False)
    art_url = forms.CharField(required=False)

    class Meta:
        model = GiftType
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        media_file = cleaned.get("media_file")
        media_url = (cleaned.get("media_url") or "").strip()
        animation_file = cleaned.get("animation_file")
        animation_url = (cleaned.get("animation_url") or "").strip()

        if media_file and media_url:
            self.add_error("media_url", "Provide either media file OR media URL, not both.")
        if animation_file and animation_url:
            self.add_error("animation_url", "Provide either animation file OR animation URL, not both.")
        effects = cleaned.get("effects")
        if effects not in (None, ""):
            from apps.payments.effects import validate_gift_effects

            try:
                cleaned["effects"] = validate_gift_effects(effects)
            except Exception as exc:  # noqa: BLE001
                self.add_error("effects", str(exc))
        return cleaned


@admin.register(GiftType)
class GiftTypeAdmin(admin.ModelAdmin):
    form = GiftTypeAdminForm
    list_display = ("id", "key", "name", "kind", "price_slc_cents", "is_active", "created_at")
    list_filter = ("kind", "is_active")
    search_fields = ("key", "name")
    ordering = ("price_slc_cents", "name")
    readonly_fields = ("media_preview_link", "animation_preview_link")
    fields = (
        "key",
        "name",
        "price_cents",
        "price_slc_cents",
        "kind",
        "media_file",
        "media_url",
        "media_preview_link",
        "animation_file",
        "animation_url",
        "animation_preview_link",
        "art_url",
        "is_active",
        "effects",
        "metadata",
    )

    def _normalize_href(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if not value.startswith("/"):
            return f"/{value}"
        return value

    def media_preview_link(self, obj: GiftType) -> str:
        href = None
        if obj.media_file and getattr(obj.media_file, "url", ""):
            href = obj.media_file.url
        elif obj.media_url:
            href = obj.media_url
        href = self._normalize_href(href)
        if not href:
            return "-"
        return format_html('<a href="{}" target="_blank" rel="noopener">Open media</a>', href)

    def animation_preview_link(self, obj: GiftType) -> str:
        href = None
        if obj.animation_file and getattr(obj.animation_file, "url", ""):
            href = obj.animation_file.url
        elif obj.animation_url:
            href = obj.animation_url
        href = self._normalize_href(href)
        if not href:
            return "-"
        return format_html('<a href="{}" target="_blank" rel="noopener">Open animation</a>', href)


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
