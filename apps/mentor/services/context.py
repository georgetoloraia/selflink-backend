from __future__ import annotations

from typing import Any


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def build_user_astro_context(user: Any) -> str:
    """
    Build a textual astro/matrix context for the LLM from the data
    that the backend already calculates for this user (Swiss Ephemeris, matrix, etc.).
    """
    parts: list[str] = []
    parts.append("User astro/matrix profile for SelfLink Mentor:")

    profile = getattr(user, "profile", None)
    personal_map = getattr(user, "personal_map", None)

    birth_date = _first_non_empty(
        getattr(profile, "birth_date", None),
        getattr(personal_map, "birth_date", None),
        getattr(user, "birth_date", None),
    )
    birth_time = _first_non_empty(
        getattr(profile, "birth_time", None),
        getattr(personal_map, "birth_time", None),
        getattr(user, "birth_time", None),
    )
    birth_city = _first_non_empty(
        getattr(profile, "birth_city", None),
        getattr(personal_map, "birth_place_city", None),
    )
    birth_country = _first_non_empty(
        getattr(profile, "birth_country", None),
        getattr(personal_map, "birth_place_country", None),
    )
    birth_place = _first_non_empty(
        getattr(user, "birth_place", None),
        ", ".join([part for part in [birth_city, birth_country] if part]),
        birth_city,
    )

    astro_profile = getattr(user, "astro_profile", None)
    sun_sign = getattr(astro_profile, "sun", None) if astro_profile else None
    moon_sign = getattr(astro_profile, "moon", None) if astro_profile else None
    ascendant_sign = getattr(astro_profile, "ascendant", None) if astro_profile else None
    descendant_sign = getattr(astro_profile, "descendant", None) if astro_profile else None

    matrix_profile = getattr(user, "matrix_data", None)
    life_path = getattr(matrix_profile, "life_path", None) if matrix_profile else None
    matrix_traits = getattr(matrix_profile, "traits", None) if matrix_profile else None

    natal_chart = getattr(user, "natal_chart", None)
    planets = getattr(natal_chart, "planets", None) if natal_chart else None
    houses = getattr(natal_chart, "houses", None) if natal_chart else None

    if birth_date:
        parts.append(f"- Birth date: {birth_date}")
    if birth_time:
        parts.append(f"- Birth time: {birth_time}")
    if birth_place:
        parts.append(f"- Birth place: {birth_place}")

    if sun_sign or moon_sign or ascendant_sign or descendant_sign:
        parts.append("")
        parts.append("Astrology highlights:")
        if sun_sign:
            parts.append(f"- Sun (core): {sun_sign}")
        if moon_sign:
            parts.append(f"- Moon (emotional nature): {moon_sign}")
        if ascendant_sign:
            parts.append(f"- Ascendant (outer image): {ascendant_sign}")
        if descendant_sign:
            parts.append(f"- Descendant (relationships): {descendant_sign}")

    if planets:
        parts.append(f"- Natal chart planets: {planets}")
    if houses:
        parts.append(f"- Houses: {houses}")

    if life_path or matrix_traits:
        parts.append("")
        parts.append("Matrix insights:")
        if life_path:
            parts.append(f"- Life path: {life_path}")
        if matrix_traits:
            parts.append(f"- Traits: {matrix_traits}")

    if len(parts) == 1:
        parts.append("- (No astro or matrix data available for this user yet.)")

    return "\n".join(parts)
