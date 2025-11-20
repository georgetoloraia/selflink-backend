from __future__ import annotations

from datetime import date
from typing import Dict

from apps.astro.models import NatalChart
from apps.matching.services.soulmatch import calculate_soulmatch
from apps.users.models import User

NATAL_MENTOR_SYSTEM_PROMPT = (
    "You are an empathetic life mentor. You use natal chart information (Sun, Moon, Ascendant, planets) "
    "as a symbolic framework to give psychological insights and practical advice about personality, emotions, "
    "relationships, career and life challenges. Avoid deterministic fortune-telling and focus on empowering the user."
)

SOULMATCH_MENTOR_SYSTEM_PROMPT = (
    "You are a relationship mentor. You help two people understand their connection using symbolic information "
    "(natal charts, values, compatibility scores). Explain attraction, potential clashes, and collaborative growth. "
    "Structure the answer into: Core Connection, Strengths, Challenges, Practical Advice. Stay supportive and realistic."
)

DAILY_MENTOR_SYSTEM_PROMPT = (
    "You are a daily life mentor. Using this person's personality profile and optional symbolic 'today' energies, "
    "give 3–5 short, practical suggestions for today: mindset, actions, relationships, and what to avoid. "
    "Be grounded, not fatalistic."
)


def build_natal_prompt(user: User, natal_chart: NatalChart) -> str:
    planets = natal_chart.planets or {}
    houses = natal_chart.houses or {}
    placements = {
        "Sun": _format_placement(planets.get("sun")),
        "Moon": _format_placement(planets.get("moon")),
        "Ascendant": houses.get("1", {}).get("sign"),
        "Venus": _format_placement(planets.get("venus")),
        "Mars": _format_placement(planets.get("mars")),
    }
    placements_text = "\n".join(f"- {k}: {v}" for k, v in placements.items() if v)

    return (
        f"User Profile:\n"
        f"- Name: {user.name or user.handle}\n"
        f"- Locale: {user.locale}\n\n"
        f"Natal Chart:\n{placements_text}\n\n"
        "Please provide a structured analysis under headings:\n"
        "1) Core Personality\n"
        "2) Emotional World\n"
        "3) Relationships & Love\n"
        "4) Career & Purpose\n"
        "5) Main Challenges & Advice\n"
    )


def build_soulmatch_prompt(user_a: User, user_b: User, soulmatch_result: Dict[str, object]) -> str:
    components = soulmatch_result.get("components", {})
    tags = soulmatch_result.get("tags", [])
    return (
        f"A user ({user_a.name or user_a.handle}) is asking about compatibility with "
        f"{user_b.name or user_b.handle}.\n\n"
        f"SoulMatch score: {soulmatch_result.get('score')}\n"
        f"Components: astro={components.get('astro')}, matrix={components.get('matrix')}, "
        f"psychology={components.get('psychology')}, lifestyle={components.get('lifestyle')}\n"
        f"Tags: {', '.join(tags)}\n\n"
        "Explain why they might feel connected, what could be challenging, and give practical advice under "
        "sections: Core Connection, Strengths, Challenges, Practical Advice."
    )


def build_daily_prompt(user: User, natal_chart: NatalChart | None) -> str:
    placements_text = ""
    if natal_chart and natal_chart.planets:
        sun = _format_placement(natal_chart.planets.get("sun"))
        moon = _format_placement(natal_chart.planets.get("moon"))
        asc = natal_chart.houses.get("1", {}).get("sign") if natal_chart.houses else None
        parts = [f"Sun: {sun}" if sun else None, f"Moon: {moon}" if moon else None, f"Asc: {asc}" if asc else None]
        placements_text = "\n".join(filter(None, parts))

    today_str = date.today().isoformat()
    return (
        f"User: {user.name or user.handle}\n"
        f"Date: {today_str}\n"
        f"Natal snapshot:\n{placements_text or 'Not provided'}\n\n"
        "Provide 3-5 bullet points with short, practical suggestions for today. "
        "Include mindset, one action, one relationship tip, and one thing to avoid."
    )


def _format_placement(data: dict | None) -> str | None:
    if not data:
        return None
    sign = data.get("sign")
    lon = data.get("lon")
    if sign and lon is not None:
        return f"{sign} {round(float(lon) % 30, 1)}°"
    if sign:
        return sign
    return None
