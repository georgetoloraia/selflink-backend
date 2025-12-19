from __future__ import annotations

import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction

from typing import Callable

from apps.astro.models import AstrologyResult, BirthData, NatalChart
from apps.astro.services import chart_calculator


def birth_data_hash(birth_data: BirthData) -> str:
    payload = {
        "date": birth_data.date_of_birth.isoformat(),
        "time": birth_data.time_of_birth.isoformat(),
        "timezone": birth_data.timezone,
        "latitude": round(float(birth_data.latitude), 6),
        "longitude": round(float(birth_data.longitude), 6),
        "city": (birth_data.city or "").strip().lower(),
        "country": (birth_data.country or "").strip().lower(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _cache_key(birth_hash: str, rules_version: str) -> str:
    return f"astro:result:{birth_hash}:{rules_version}"


def get_cached_or_compute(
    birth_data: BirthData,
    rules_version: str | None = None,
    calculate_fn: Callable[[BirthData], NatalChart] | None = None,
) -> tuple[AstrologyResult, NatalChart]:
    rules_version = rules_version or getattr(settings, "ASTRO_RULES_VERSION", "v1")
    birth_hash = birth_data_hash(birth_data)
    cache_key = _cache_key(birth_hash, rules_version)

    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        result = AstrologyResult.objects.filter(
            birth_data_hash=birth_hash,
            rules_version=rules_version,
        ).first()
        chart = NatalChart.objects.filter(birth_data=birth_data).first()
        if result and chart:
            return result, chart

    result = AstrologyResult.objects.filter(
        birth_data_hash=birth_hash,
        rules_version=rules_version,
    ).first()
    chart = NatalChart.objects.filter(birth_data=birth_data).first()
    if result and chart:
        cache.set(cache_key, result.payload_json, timeout=getattr(settings, "ASTRO_CACHE_TTL_SECONDS", 0))
        return result, chart

    calculator = calculate_fn or chart_calculator.calculate_natal_chart
    chart = calculator(birth_data)
    payload = {"planets": chart.planets, "houses": chart.houses, "aspects": chart.aspects}

    try:
        with transaction.atomic():
            result = AstrologyResult.objects.create(
                birth_data_hash=birth_hash,
                rules_version=rules_version,
                payload_json=payload,
            )
    except IntegrityError:
        result = AstrologyResult.objects.get(
            birth_data_hash=birth_hash,
            rules_version=rules_version,
        )

    cache.set(cache_key, result.payload_json, timeout=getattr(settings, "ASTRO_CACHE_TTL_SECONDS", 0))
    return result, chart
