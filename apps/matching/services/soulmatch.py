from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from apps.astro.models import NatalChart
from apps.profile.models import UserProfile
from apps.users.models import User

ELEMENTS_BY_SIGN = {
    "Aries": "fire",
    "Leo": "fire",
    "Sagittarius": "fire",
    "Taurus": "earth",
    "Virgo": "earth",
    "Capricorn": "earth",
    "Gemini": "air",
    "Libra": "air",
    "Aquarius": "air",
    "Cancer": "water",
    "Scorpio": "water",
    "Pisces": "water",
}


@dataclass
class SoulmatchScores:
    astro: float = 0
    matrix: float = 15  # neutral stub
    psychology: float = 0
    lifestyle: float = 0

    @property
    def total(self) -> int:
        total = self.astro + self.matrix + self.psychology + self.lifestyle
        return int(round(min(max(total, 0), 100)))


def _dominant_element(chart: Optional[NatalChart]) -> Optional[str]:
    if not chart or not chart.planets:
        return None
    signs = []
    for key in ("sun", "moon"):
        if key in chart.planets:
            signs.append(chart.planets[key].get("sign"))
    asc_sign = chart.houses.get("1", {}).get("sign") if getattr(chart, "houses", None) else None
    if asc_sign:
        signs.append(asc_sign)

    elements = [ELEMENTS_BY_SIGN.get(s) for s in signs if s in ELEMENTS_BY_SIGN]
    if not elements:
        return None
    return max(set(elements), key=elements.count)


def _astro_score(element_a: Optional[str], element_b: Optional[str], chart_a: NatalChart | None, chart_b: NatalChart | None) -> float:
    if not element_a or not element_b:
        return 0.0
    if element_a == element_b:
        return 35.0
    good_pairs = {("fire", "air"), ("air", "fire"), ("water", "earth"), ("earth", "water")}
    if (element_a, element_b) in good_pairs:
        return 30.0
    venus_a = chart_a.planets.get("venus", {}).get("sign") if chart_a else None
    mars_b = chart_b.planets.get("mars", {}).get("sign") if chart_b else None
    if venus_a and mars_b and ELEMENTS_BY_SIGN.get(venus_a) == ELEMENTS_BY_SIGN.get(mars_b):
        return 25.0
    return 15.0


def _overlap_score(list_a: List[str], list_b: List[str], max_points: float) -> float:
    set_a, set_b = set(list_a or []), set(list_b or [])
    if not set_a and not set_b:
        return max_points / 2
    if not set_a or not set_b:
        return max_points / 3
    common = len(set_a & set_b)
    unique = len(set_a | set_b)
    ratio = common / unique if unique else 0
    return round(ratio * max_points, 2)


def _attachment_score(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 5.0
    if a == "secure" or b == "secure":
        return 8.0
    if {a, b} == {"anxious", "avoidant"}:
        return 2.0
    return 5.0


def _psychology_score(profile_a: UserProfile | None, profile_b: UserProfile | None) -> float:
    if not profile_a or not profile_b:
        return 0.0
    values_score = _overlap_score(getattr(profile_a, "values", []), getattr(profile_b, "values", []), max_points=15)
    attachment = _attachment_score(
        getattr(profile_a, "attachment_style", None), getattr(profile_b, "attachment_style", None)
    )
    return min(values_score + attachment, 20.0)


def _lifestyle_score(profile_a: UserProfile | None, profile_b: UserProfile | None) -> float:
    if not profile_a or not profile_b:
        return 0.0
    lifestyle = _overlap_score(
        getattr(profile_a, "preferred_lifestyle", []),
        getattr(profile_b, "preferred_lifestyle", []),
        max_points=10,
    )
    love_lang = _overlap_score(
        getattr(profile_a, "love_language", []),
        getattr(profile_b, "love_language", []),
        max_points=5,
    )
    return min(lifestyle + love_lang, 10.0)


def _generate_tags(scores: SoulmatchScores) -> List[str]:
    if scores.astro == 0 and scores.psychology == 0 and scores.lifestyle == 0:
        return ["neutral"]
    tags: List[str] = []
    if scores.astro > 30 and scores.psychology > 15:
        tags.append("soulmate_like")
    if scores.astro > 30 and scores.psychology < 10:
        tags.append("strong_chemistry_needs_work")
    if scores.lifestyle > 7:
        tags.append("aligned_lifestyle")
    if scores.psychology > 12:
        tags.append("values_aligned")
    if scores.total < 40:
        tags.append("growth_opportunity")
    return tags or ["neutral"]


def calculate_soulmatch(user_a: User, user_b: User) -> Dict[str, object]:
    if user_a.id == user_b.id:
        raise ValueError("Cannot compute SoulMatch for the same user.")

    profile_a = UserProfile.objects.filter(user_id=user_a.id).first()
    profile_b = UserProfile.objects.filter(user_id=user_b.id).first()
    if profile_a and profile_a.is_empty():
        profile_a = None
    if profile_b and profile_b.is_empty():
        profile_b = None
    chart_a = getattr(user_a, "natal_chart", None)
    chart_b = getattr(user_b, "natal_chart", None)

    dominant_a = _dominant_element(chart_a)
    dominant_b = _dominant_element(chart_b)
    astro_score = _astro_score(dominant_a, dominant_b, chart_a, chart_b)
    psych_score = _psychology_score(profile_a, profile_b)
    lifestyle_score = _lifestyle_score(profile_a, profile_b)

    scores = SoulmatchScores(
        astro=astro_score,
        psychology=psych_score,
        lifestyle=lifestyle_score,
    )

    result = {
        "user_id": user_b.id,
        "score": scores.total,
        "components": {
            "astro": scores.astro,
            "matrix": scores.matrix,
            "psychology": scores.psychology,
            "lifestyle": scores.lifestyle,
        },
        "tags": _generate_tags(scores),
    }
    return result
