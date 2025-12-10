from __future__ import annotations

import logging
from typing import Dict, List

from django.db import transaction
from django.conf import settings
from django.core.cache import cache

from apps.astro.models import BirthData, NatalChart
from apps.astro.services import ephemeris

logger = logging.getLogger(__name__)

SIGN_NAMES = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

ASPECT_ANGLES = {
    "conjunction": 0,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

_CACHE_TTL = getattr(settings, "ASTRO_CACHE_TTL_SECONDS", 60 * 60 * 24 * 7)
_RULES_VERSION = getattr(settings, "ASTRO_RULES_VERSION", "v1")


def degree_to_sign(degree: float) -> str:
    return SIGN_NAMES[int(degree % 360 // 30)]


def _build_houses(ascendant_lon: float) -> Dict[str, Dict[str, float | str]]:
    houses: Dict[str, Dict[str, float | str]] = {}
    for house_num in range(1, 13):
        cusp = (ascendant_lon + (house_num - 1) * 30) % 360
        houses[str(house_num)] = {
            "cusp_lon": float(cusp),
            "sign": degree_to_sign(cusp),
        }
    return houses


def _compute_aspects(planets: Dict[str, Dict[str, float]], orb: float = 3.0) -> List[Dict[str, float | str]]:
    aspect_list: List[Dict[str, float | str]] = []
    planet_names = [name for name in planets.keys() if name not in {"asc", "mc"}]
    for i, p1 in enumerate(planet_names):
        for p2 in planet_names[i + 1 :]:
            angle = abs(planets[p1]["lon"] - planets[p2]["lon"]) % 360
            normalized = min(angle, 360 - angle)
            for aspect_name, target in ASPECT_ANGLES.items():
                diff = abs(normalized - target)
                if diff <= orb:
                    aspect_list.append(
                        {"p1": p1, "p2": p2, "aspect": aspect_name, "orb": round(diff, 2)}
                    )
                    break
    return aspect_list


def _enrich_planets(positions: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float | str]]:
    enriched: Dict[str, Dict[str, float | str]] = {}
    for name, data in positions.items():
        enriched[name] = {**data, "sign": degree_to_sign(data["lon"])}
    return enriched


def _cache_key(birth_data: BirthData) -> str:
    return (
        f"astro:natal:{birth_data.user_id}:"
        f"{birth_data.date_of_birth}:{birth_data.time_of_birth}:"
        f"{birth_data.latitude}:{birth_data.longitude}:{birth_data.timezone}:"
        f"{_RULES_VERSION}"
    )


@transaction.atomic
def calculate_natal_chart(birth_data: BirthData) -> NatalChart:
    logger.info("Calculating natal chart", extra={"user_id": birth_data.user_id})

    birth_data.full_clean()

    cache_key = _cache_key(birth_data)
    cached_chart_id = cache.get(cache_key)
    if cached_chart_id:
        try:
            return NatalChart.objects.get(id=cached_chart_id)
        except NatalChart.DoesNotExist:
            cache.delete(cache_key)

    julian_day = ephemeris.to_julian_day(
        birth_data.date_of_birth,
        birth_data.time_of_birth,
        birth_data.timezone,
        birth_data.latitude,
        birth_data.longitude,
    )
    positions = ephemeris.get_planet_positions(julian_day, birth_data.latitude, birth_data.longitude)

    ascendant = positions.get("asc", {}).get("lon", 0.0)
    houses = _build_houses(ascendant)
    planets = _enrich_planets({k: v for k, v in positions.items() if k not in {"asc", "mc"}})
    aspects = _compute_aspects(planets)

    chart_data = {
        "planets": planets,
        "houses": houses,
        "aspects": aspects,
    }

    chart, _ = NatalChart.objects.update_or_create(
        user=birth_data.user,
        defaults={
            "birth_data": birth_data,
            "planets": chart_data["planets"],
            "houses": chart_data["houses"],
            "aspects": chart_data["aspects"],
        },
    )
    cache.set(cache_key, chart.id, timeout=_CACHE_TTL)
    return chart
