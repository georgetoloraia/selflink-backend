from __future__ import annotations

from django.conf import settings


def payments_enabled() -> bool:
    flags = getattr(settings, "FEATURE_FLAGS", {})
    return flags.get("payments", False)
