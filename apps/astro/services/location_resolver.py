from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict
from zoneinfo import ZoneInfo

from apps.profile.models import UserProfile

logger = logging.getLogger(__name__)


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


def resolve_location_from_profile(profile: UserProfile) -> ResolvedLocation:
    """
    Resolve or validate timezone and coordinates for a user's profile birth data.
    Placeholder logic: returns existing valid values or defaults.
    """
    if profile.birth_timezone and profile.birth_latitude is not None and profile.birth_longitude is not None:
        _validate_timezone(profile.birth_timezone)
        _validate_coords(profile.birth_latitude, profile.birth_longitude)
        return ResolvedLocation(
            timezone=profile.birth_timezone,
            latitude=profile.birth_latitude,
            longitude=profile.birth_longitude,
        )

    # Placeholder resolution: default to configured timezone and static coords
    # This is structured for future geocoding integration.
    default_timezone = "Asia/Tbilisi"
    default_lat, default_lon = 41.7167, 44.7833

    if not profile.birth_city or not profile.birth_country:
        raise LocationResolutionError("Missing birth city or country for location resolution.")

    logger.info(
        "Using fallback location resolution for profile",
        extra={"user_id": profile.user_id, "city": profile.birth_city, "country": profile.birth_country},
    )

    _validate_timezone(default_timezone)
    _validate_coords(default_lat, default_lon)
    return ResolvedLocation(timezone=default_timezone, latitude=default_lat, longitude=default_lon)
