from __future__ import annotations

import re
from secrets import token_hex

from .models import User


def normalize_handle(value: str, max_length: int) -> str:
    cleaned = re.sub(r"[^a-z0-9_]", "", value.lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_length]


def generate_unique_handle(name: str, email: str, max_length: int) -> str:
    candidates = [name, email.split("@", 1)[0], "selflink"]
    for candidate in candidates:
        normalized = normalize_handle(candidate or "", max_length)
        if normalized and not User.objects.filter(handle=normalized).exists():
            return normalized

    base = normalize_handle(name or "selflink", max_length) or "selflink"
    suffix_length = 4
    while True:
        suffix = token_hex(suffix_length // 2)
        trim_length = max_length - len(suffix)
        prefix = base[:trim_length] if trim_length > 0 else ""
        candidate = f"{prefix}{suffix}"
        if not User.objects.filter(handle=candidate).exists():
            return candidate
