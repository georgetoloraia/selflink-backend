from __future__ import annotations

from datetime import date, time
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.astro.models import BirthData, NatalChart
from apps.astro.services.chart_calculator import calculate_natal_chart
from apps.users.models import User


class BirthDataValidationTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="astro@example.com", password="pass123", handle="astro", name="Astro")

    def test_rejects_invalid_timezone(self) -> None:
        birth_data = BirthData(
            user=self.user,
            date_of_birth=date(1990, 1, 1),
            time_of_birth=time(12, 0),
            timezone="Invalid/Zone",
            latitude=10.0,
            longitude=10.0,
        )
        with self.assertRaises(ValidationError) as exc:
            birth_data.full_clean()
        self.assertIn("timezone", exc.exception.error_dict)

    def test_rejects_invalid_coordinates(self) -> None:
        birth_data = BirthData(
            user=self.user,
            date_of_birth=date(1990, 1, 1),
            time_of_birth=time(12, 0),
            timezone="UTC",
            latitude=120.0,
            longitude=-200.0,
        )
        with self.assertRaises(ValidationError) as exc:
            birth_data.full_clean()
        self.assertIn("latitude", exc.exception.error_dict)
        self.assertIn("longitude", exc.exception.error_dict)


class ChartCalculatorTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="astro2@example.com", password="pass123", handle="astro2", name="Astro Two")

    @mock.patch("apps.astro.services.chart_calculator.ephemeris.get_planet_positions")
    @mock.patch("apps.astro.services.chart_calculator.ephemeris.to_julian_day")
    def test_calculate_natal_chart_persists_chart(self, mock_jd: mock.Mock, mock_positions: mock.Mock) -> None:
        mock_jd.return_value = 2450000.0
        mock_positions.return_value = {
            "sun": {"lon": 0.0, "speed": 1.0},
            "moon": {"lon": 120.0, "speed": 0.5},
            "mercury": {"lon": 90.0, "speed": 1.2},
            "venus": {"lon": 200.0, "speed": 1.1},
            "mars": {"lon": 280.0, "speed": 0.8},
            "jupiter": {"lon": 310.0, "speed": 0.6},
            "saturn": {"lon": 340.0, "speed": 0.4},
            "uranus": {"lon": 10.0, "speed": 0.3},
            "neptune": {"lon": 150.0, "speed": 0.3},
            "pluto": {"lon": 210.0, "speed": 0.2},
            "asc": {"lon": 15.0},
            "mc": {"lon": 250.0},
        }

        birth_data = BirthData.objects.create(
            user=self.user,
            date_of_birth=date(1990, 1, 1),
            time_of_birth=time(12, 0),
            timezone="UTC",
            latitude=37.7749,
            longitude=-122.4194,
        )

        chart = calculate_natal_chart(birth_data)

        self.assertIsInstance(chart, NatalChart)
        self.assertEqual(chart.user_id, self.user.id)
        self.assertEqual(chart.planets["sun"]["sign"], "Aries")
        self.assertEqual(chart.planets["moon"]["sign"], "Leo")
        self.assertIn("1", chart.houses)
        self.assertEqual(chart.houses["1"]["sign"], "Aries")
        # aspects should catch the Sun-Moon trine and Sun-Mercury square with a small orb
        aspect_names = {a["aspect"] for a in chart.aspects}
        self.assertIn("trine", aspect_names)
        self.assertIn("square", aspect_names)
        mock_jd.assert_called_once()
        mock_positions.assert_called_once()
