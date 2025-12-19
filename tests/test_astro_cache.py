from __future__ import annotations

from datetime import date, time

from apps.astro.cache import birth_data_hash
from apps.astro.models import BirthData


def _birth_data(**overrides) -> BirthData:
    data = {
        "user_id": 1,
        "date_of_birth": date(1990, 1, 1),
        "time_of_birth": time(12, 0),
        "timezone": "UTC",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "city": "San Francisco",
        "country": "USA",
    }
    data.update(overrides)
    return BirthData(**data)


def test_birth_data_hash_is_stable():
    first = _birth_data()
    second = _birth_data()
    assert birth_data_hash(first) == birth_data_hash(second)


def test_birth_data_hash_changes_with_location():
    first = _birth_data()
    second = _birth_data(latitude=40.7128)
    assert birth_data_hash(first) != birth_data_hash(second)

