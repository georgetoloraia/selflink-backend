from __future__ import annotations

from datetime import date
from typing import Tuple

from apps.users.models import User


def compute_life_path(birth_date: date | None) -> Tuple[str, dict]:
    if not birth_date:
        return "", {}
    digits = [int(ch) for ch in birth_date.strftime("%Y%m%d")]
    total = sum(digits)
    while total > 9 and total not in {11, 22, 33}:
        total = sum(int(ch) for ch in str(total))
    traits = {
        1: "Initiator",
        2: "Diplomat",
        3: "Creator",
        4: "Builder",
        5: "Explorer",
        6: "Nurturer",
        7: "Seeker",
        8: "Leader",
        9: "Humanitarian",
        11: "Visionary",
        22: "Architect",
        33: "Guide",
    }
    return str(total), {"primary_trait": traits.get(total, "Mystic"), "raw_sum": total}


def default_traits(user: User) -> dict:
    life_path, traits = compute_life_path(user.birth_date)
    traits.update({"sun": getattr(user, "astro_profile", None) and user.astro_profile.sun})
    return {k: v for k, v in traits.items() if v}
