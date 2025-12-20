from __future__ import annotations

import logging

from apps.astro.models import BirthData
from apps.astro.services import location_resolver
from apps.profile.models import UserProfile
from apps.users.models import User

logger = logging.getLogger(__name__)


class BirthDataIncompleteError(Exception):
    """Raised when required birth fields are missing on the profile."""


def _validate_profile_birth_fields(profile: UserProfile) -> None:
    missing = []
    if not profile.birth_date:
        missing.append("birth_date")
    if profile.birth_time is None:
        missing.append("birth_time")
    if not profile.birth_city:
        missing.append("birth_city")
    if not profile.birth_country:
        missing.append("birth_country")
    if missing:
        raise BirthDataIncompleteError(", ".join(missing))


def create_or_update_birth_data_from_profile(user: User) -> BirthData:
    profile = getattr(user, "profile", None)
    personal_map = getattr(user, "personal_map", None)

    # Gather birth fields from profile, personal map, or user fields
    birth_date = getattr(profile, "birth_date", None) or getattr(personal_map, "birth_date", None) or getattr(user, "birth_date", None)
    birth_time = getattr(profile, "birth_time", None) or getattr(personal_map, "birth_time", None) or getattr(user, "birth_time", None)
    birth_city = getattr(profile, "birth_city", None) or getattr(personal_map, "birth_place_city", None) or ""
    birth_country = getattr(profile, "birth_country", None) or getattr(personal_map, "birth_place_country", None) or ""

    if not birth_date or birth_time is None or not birth_city or not birth_country:
        raise BirthDataIncompleteError("birth_date, birth_time, birth_city, birth_country")

    # Ensure we have a profile instance to store resolved location
    if profile is None:
        # lazily create a minimal profile to hold resolved fields
        profile = UserProfile.objects.create(
            user=user,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_city=birth_city,
            birth_country=birth_country,
        )

    profile.birth_date = profile.birth_date or birth_date
    profile.birth_time = profile.birth_time or birth_time
    profile.birth_city = profile.birth_city or birth_city
    profile.birth_country = profile.birth_country or birth_country

    try:
        resolved = location_resolver.resolve_location_from_profile(profile)
    except location_resolver.LocationResolutionError:
        raise
    except Exception:
        logger.exception("Unexpected error resolving location", extra={"user_id": user.id})
        raise

    profile.birth_timezone = resolved.timezone
    profile.birth_latitude = resolved.latitude
    profile.birth_longitude = resolved.longitude
    profile.save(
        update_fields=[
            "birth_timezone",
            "birth_latitude",
            "birth_longitude",
            "birth_date",
            "birth_time",
            "birth_city",
            "birth_country",
            "updated_at",
        ],
    )

    birth_data, _ = BirthData.objects.update_or_create(
        user=user,
        defaults={
            "date_of_birth": birth_date,
            "time_of_birth": birth_time,
            "timezone": resolved.timezone,
            "city": birth_city,
            "country": birth_country,
            "latitude": resolved.latitude,
            "longitude": resolved.longitude,
        },
    )
    return birth_data
