from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from typing import Dict, Mapping
from zoneinfo import ZoneInfo

from django.conf import settings

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover - guarded by requirements
    raise RuntimeError("pyswisseph is required for astrology calculations") from exc

logger = logging.getLogger(__name__)


class AstroCalculationError(Exception):
    """Raised when ephemeris calculations fail or inputs are invalid."""


PLANET_MAP: Mapping[str, int] = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
}


def _set_ephe_path() -> str:
    ephe_path = str(getattr(settings, "SWISSEPH_DATA_PATH", "") or "")
    swe.set_ephe_path(ephe_path)
    return ephe_path


def _validate_coordinates(latitude: float, longitude: float) -> None:
    if not -90 <= latitude <= 90:
        raise AstroCalculationError(f"Latitude {latitude} out of range (-90 to 90).")
    if not -180 <= longitude <= 180:
        raise AstroCalculationError(f"Longitude {longitude} out of range (-180 to 180).")


def to_julian_day(input_date: date, input_time: time, timezone_str: str, latitude: float, longitude: float) -> float:
    """
    Convert a local date/time and coordinates to Julian Day (UT).
    Timezone handling is explicit to avoid accidental naive conversions.
    """
    _validate_coordinates(latitude, longitude)

    try:
        tzinfo = ZoneInfo(timezone_str)
    except Exception as exc:
        raise AstroCalculationError(f"Invalid timezone '{timezone_str}'.") from exc

    try:
        local_dt = datetime.combine(input_date, input_time, tzinfo=tzinfo)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise AstroCalculationError("Invalid date or time values.") from exc

    dt_utc = local_dt.astimezone(timezone.utc)
    logger.debug("Converting to Julian Day", extra={"tz": timezone_str})

    ut_hours = (
        dt_utc.hour
        + dt_utc.minute / 60
        + dt_utc.second / 3600
        + dt_utc.microsecond / 3_600_000_000
    )

    try:
        julian_day = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, ut_hours, swe.GREG_CAL)
    except Exception as exc:
        raise AstroCalculationError("Failed to compute Julian Day.") from exc

    return julian_day


def get_planet_positions(julian_day: float, latitude: float, longitude: float) -> Dict[str, Dict[str, float]]:
    """
    Calculate ecliptic longitudes/speeds for major planets plus Ascendant and Midheaven.
    """
    _validate_coordinates(latitude, longitude)
    ephe_path = _set_ephe_path()
    logger.debug("Calculating planet positions", extra={"ephe_path": ephe_path})

    try:
        swisseph_flag = swe.FLG_SWIEPH | swe.FLG_SPEED
        positions: Dict[str, Dict[str, float]] = {}

        for name, planet_id in PLANET_MAP.items():
            result = swe.calc_ut(julian_day, planet_id, swisseph_flag)
            if isinstance(result, (list, tuple)) and len(result) >= 3:
                # some builds return (lon, lat, dist) when speed is unavailable; some return 6 values
                lon = result[0]
                lon_speed = result[3] if len(result) >= 4 else 0.0
            else:
                raise AstroCalculationError("Unexpected response from swisseph calc_ut")
            positions[name] = {
                "lon": float(lon),
                "speed": float(lon_speed),
            }

        houses, ascmc = swe.houses_ex(julian_day, latitude, longitude, b"P")
        positions["asc"] = {"lon": float(ascmc[0])}
        positions["mc"] = {"lon": float(ascmc[1])}
    except Exception as exc:
        message = "Ephemeris calculation failed. Ensure ephemeris files exist and inputs are in range."
        logger.exception(message)
        raise AstroCalculationError(message) from exc

    return positions
