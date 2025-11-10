from __future__ import annotations

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import User, UserSettings
from .utils import generate_unique_handle


class SelflinkSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Ensure required user fields exist when signing up via social auth."""

    def save_user(self, request, sociallogin, form=None):  # type: ignore[override]
        user: User = sociallogin.user  # type: ignore[assignment]
        extra_data = sociallogin.account.extra_data or {}
        user.email = user.email or extra_data.get("email")

        display_name = self._extract_name(extra_data)
        if display_name:
            user.name = display_name
        if not user.name:
            user.name = (user.email or "user@selflink.app").split("@", 1)[0]

        if not user.handle:
            max_length = User._meta.get_field("handle").max_length
            user.handle = generate_unique_handle(user.name, user.email, max_length)

        response = super().save_user(request, sociallogin, form=form)
        UserSettings.objects.get_or_create(user=user)
        return response

    def _extract_name(self, extra_data: dict) -> str:
        candidates = [
            extra_data.get("name"),
            " ".join(part for part in [extra_data.get("first_name"), extra_data.get("last_name")] if part),
            " ".join(part for part in [extra_data.get("given_name"), extra_data.get("family_name")] if part),
        ]
        for candidate in candidates:
            if candidate and candidate.strip():
                return candidate.strip()
        return ""
