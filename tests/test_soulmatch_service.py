from __future__ import annotations

from datetime import date, time

from django.test import TestCase

from apps.astro.models import BirthData, NatalChart
from apps.matching.services.soulmatch import calculate_soulmatch
from apps.profile.models import UserProfile
from apps.users.models import User


def _make_chart(user: User, asc_sign: str, sun_sign: str, moon_sign: str) -> NatalChart:
    birth_data = BirthData.objects.create(
        user=user,
        date_of_birth=date(1990, 1, 1),
        time_of_birth=time(12, 0),
        timezone="UTC",
        latitude=0.0,
        longitude=0.0,
    )
    return NatalChart.objects.create(
        user=user,
        birth_data=birth_data,
        planets={
            "sun": {"lon": 0.0, "sign": sun_sign},
            "moon": {"lon": 120.0, "sign": moon_sign},
            "venus": {"lon": 30.0, "sign": sun_sign},
            "mars": {"lon": 45.0, "sign": moon_sign},
        },
        houses={"1": {"cusp_lon": 0.0, "sign": asc_sign}},
        aspects=[],
    )


class SoulmatchServiceTests(TestCase):
    def setUp(self) -> None:
        self.user_a = User.objects.create_user(email="a@example.com", password="pass123", handle="a", name="User A")
        self.user_b = User.objects.create_user(email="b@example.com", password="pass123", handle="b", name="User B")

    def test_high_astro_and_psych_tags(self) -> None:
        _make_chart(self.user_a, "Aries", "Aries", "Leo")
        _make_chart(self.user_b, "Leo", "Leo", "Sagittarius")
        UserProfile.objects.create(
            user=self.user_a,
            values=["growth", "freedom"],
            preferred_lifestyle=["travel"],
            attachment_style="secure",
            love_language=["words"],
        )
        UserProfile.objects.create(
            user=self.user_b,
            values=["growth", "freedom", "connection"],
            preferred_lifestyle=["travel", "remote_work"],
            attachment_style="secure",
            love_language=["words", "touch"],
        )

        result = calculate_soulmatch(self.user_a, self.user_b)
        self.assertGreaterEqual(result["components"]["astro"], 30)
        self.assertGreaterEqual(result["components"]["psychology"], 15)
        self.assertIn("soulmate_like", result["tags"])

    def test_missing_charts_returns_neutral_matrix_and_low_astro(self) -> None:
        result = calculate_soulmatch(self.user_a, self.user_b)
        self.assertEqual(result["components"]["astro"], 0)
        self.assertEqual(result["components"]["matrix"], 15)
        self.assertIn("neutral", result["tags"])

    def test_lifestyle_overlap_scores(self) -> None:
        UserProfile.objects.create(
            user=self.user_a,
            preferred_lifestyle=["travel", "fitness"],
            love_language=["words", "gifts"],
        )
        UserProfile.objects.create(
            user=self.user_b,
            preferred_lifestyle=["travel"],
            love_language=["gifts"],
        )
        result = calculate_soulmatch(self.user_a, self.user_b)
        self.assertGreater(result["components"]["lifestyle"], 0)
        self.assertGreater(result["score"], 0)

    def test_same_user_raises(self) -> None:
        with self.assertRaises(ValueError):
            calculate_soulmatch(self.user_a, self.user_a)
