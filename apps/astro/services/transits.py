from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from apps.astro.services import ephemeris


def get_today_transits(latitude: float, longitude: float) -> Dict[str, Dict[str, float]]:
    """
    Compute Sun and Moon positions for the current UTC datetime.
    """
    now = datetime.now(timezone.utc)
    julian_day = ephemeris.to_julian_day(now.date(), now.timetz(), "UTC", latitude, longitude)
    positions = ephemeris.get_planet_positions(julian_day, latitude, longitude)
    return {
        "sun_today": positions.get("sun"),
        "moon_today": positions.get("moon"),
    }
