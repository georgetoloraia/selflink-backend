from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.payments.models import GiftType


@pytest.mark.django_db
def test_gift_effects_rejects_unknown_type() -> None:
    gift = GiftType(
        key="bad_effect",
        name="Bad Effect",
        price_cents=100,
        price_slc_cents=100,
        effects={"version": 2, "effects": [{"type": "sparkle"}]},
    )
    with pytest.raises(ValidationError):
        gift.full_clean()


@pytest.mark.django_db
def test_gift_effects_require_overlay_animation() -> None:
    gift = GiftType(
        key="bad_overlay",
        name="Bad Overlay",
        price_cents=100,
        price_slc_cents=100,
        effects={"version": 2, "effects": [{"type": "overlay", "scope": "post"}]},
    )
    with pytest.raises(ValidationError):
        gift.full_clean()


@pytest.mark.django_db
def test_gift_effects_normalize_defaults() -> None:
    gift = GiftType(
        key="good_effect",
        name="Good Effect",
        price_cents=100,
        price_slc_cents=100,
        effects={"effects": [{"type": "badge", "text": "OK"}]},
    )
    gift.full_clean()
    assert gift.effects.get("version") == 2
    assert gift.effects.get("persist", {}).get("mode") == "none"
    assert gift.effects.get("persist", {}).get("window_seconds") == 0
