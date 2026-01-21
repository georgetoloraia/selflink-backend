from __future__ import annotations

from django.conf import settings


def payments_enabled() -> bool:
    flags = getattr(settings, "FEATURE_FLAGS", {})
    return flags.get("payments", False)


def provider_enabled(name: str) -> bool:
    if not payments_enabled():
        return False
    setting_name = f"PAYMENTS_PROVIDER_ENABLED_{name.upper()}"
    return bool(getattr(settings, setting_name, True))
