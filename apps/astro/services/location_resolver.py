from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict
from zoneinfo import ZoneInfo

from apps.profile.models import UserProfile

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from timezonefinder import TimezoneFinder
except Exception:  # pragma: no cover - graceful fallback
    TimezoneFinder = None  # type: ignore


class LocationResolutionError(Exception):
    """Raised when timezone/coordinates cannot be resolved or validated."""


@dataclass
class ResolvedLocation:
    timezone: str
    latitude: float
    longitude: float

    def as_dict(self) -> Dict[str, float | str]:
        return {
            "timezone": self.timezone,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


_DEFAULT_TIMEZONE = "Asia/Tbilisi"
_DEFAULT_LAT = 41.7167
_DEFAULT_LON = 44.7833
_tz_finder: TimezoneFinder | None = None  # type: ignore[valid-type]


def _validate_timezone(tz: str) -> None:
    try:
        ZoneInfo(tz)
    except Exception as exc:
        raise LocationResolutionError(f"Invalid timezone '{tz}'.") from exc


def _validate_coords(lat: float, lon: float) -> None:
    if not -90 <= lat <= 90:
        raise LocationResolutionError("Latitude must be between -90 and 90.")
    if not -180 <= lon <= 180:
        raise LocationResolutionError("Longitude must be between -180 and 180.")


def _resolve_timezone_from_coordinates(latitude: float, longitude: float, default: str | None = None) -> str:
    """
    Resolve timezone string from coordinates using timezonefinder when available.
    Falls back to provided default on failure.
    """
    _validate_coords(latitude, longitude)
    if TimezoneFinder is None:
        if default:
            _validate_timezone(default)
            return default
        raise LocationResolutionError("Timezone resolution is unavailable (timezonefinder not installed).")

    global _tz_finder
    if _tz_finder is None:
        _tz_finder = TimezoneFinder()

    tz = _tz_finder.timezone_at(lat=latitude, lng=longitude)
    if not tz and default:
        tz = default
    if not tz:
        raise LocationResolutionError("Unable to resolve timezone for provided coordinates.")
    _validate_timezone(tz)
    return tz


def resolve_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """Public helper for consumers that need timezone-only resolution."""
    return _resolve_timezone_from_coordinates(latitude, longitude, default=_DEFAULT_TIMEZONE)


def resolve_location_from_profile(profile: UserProfile) -> ResolvedLocation:
    """
    Resolve or validate timezone and coordinates for a user's profile birth data.
    Coordinates, when present, take precedence over text location.
    """
    if profile.birth_latitude is not None and profile.birth_longitude is not None:
        timezone = profile.birth_timezone or _resolve_timezone_from_coordinates(
            profile.birth_latitude, profile.birth_longitude, default=_DEFAULT_TIMEZONE
        )
        _validate_timezone(timezone)
        return ResolvedLocation(
            timezone=timezone,
            latitude=profile.birth_latitude,
            longitude=profile.birth_longitude,
        )

    if not profile.birth_city or not profile.birth_country:
        raise LocationResolutionError("Missing birth city or country for location resolution.")

    logger.info(
        "Using fallback location resolution for profile",
        extra={"user_id": profile.user_id, "city": profile.birth_city, "country": profile.birth_country},
    )

    _validate_timezone(_DEFAULT_TIMEZONE)
    _validate_coords(_DEFAULT_LAT, _DEFAULT_LON)
    return ResolvedLocation(timezone=_DEFAULT_TIMEZONE, latitude=_DEFAULT_LAT, longitude=_DEFAULT_LON)


def resolve_location(city: str, country: str, latitude: float | None = None, longitude: float | None = None) -> ResolvedLocation:
    """
    Resolve timezone/coords from city/country or explicit coordinates.
    Coordinates override text location when provided.
    """
    if latitude is not None and longitude is not None:
        timezone = _resolve_timezone_from_coordinates(latitude, longitude, default=_DEFAULT_TIMEZONE)
        return ResolvedLocation(timezone=timezone, latitude=latitude, longitude=longitude)

    if not city or not country:
        raise LocationResolutionError("Missing city or country for location resolution.")

    _validate_timezone(_DEFAULT_TIMEZONE)
    _validate_coords(_DEFAULT_LAT, _DEFAULT_LON)
    return ResolvedLocation(timezone=_DEFAULT_TIMEZONE, latitude=_DEFAULT_LAT, longitude=_DEFAULT_LON)
