from __future__ import annotations

from django.conf import settings


def is_enabled() -> bool:
    flags = getattr(settings, "FEATURE_FLAGS", {})
    return flags.get("soulmatch", False)
