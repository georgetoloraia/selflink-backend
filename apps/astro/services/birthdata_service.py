from __future__ import annotations

import logging

from apps.astro.models import BirthData
from apps.astro.services.location_resolver import LocationResolutionError, resolve_location_from_profile
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
    try:
        profile = user.profile
    except UserProfile.DoesNotExist as exc:
        raise BirthDataIncompleteError("Profile missing for user.") from exc

    _validate_profile_birth_fields(profile)

    try:
        resolved = resolve_location_from_profile(profile)
    except LocationResolutionError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error resolving location", extra={"user_id": user.id})
        raise

    # Persist resolved fields on profile
    profile.birth_timezone = resolved.timezone
    profile.birth_latitude = resolved.latitude
    profile.birth_longitude = resolved.longitude
    profile.save(
        update_fields=["birth_timezone", "birth_latitude", "birth_longitude", "updated_at"],
    )

    birth_data, _ = BirthData.objects.update_or_create(
        user=user,
        defaults={
            "date_of_birth": profile.birth_date,
            "time_of_birth": profile.birth_time,
            "timezone": resolved.timezone,
            "city": profile.birth_city,
            "country": profile.birth_country,
            "latitude": resolved.latitude,
            "longitude": resolved.longitude,
        },
    )
    return birth_data
