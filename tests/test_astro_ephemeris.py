from __future__ import annotations

from datetime import date, time
from unittest import mock

from django.test import SimpleTestCase

from apps.astro.services import ephemeris


class EphemerisTests(SimpleTestCase):
    def test_to_julian_day_matches_swisseph_helper(self) -> None:
        jd = ephemeris.to_julian_day(date(2024, 1, 1), time(12, 0), "UTC", 0.0, 0.0)
        expected = ephemeris.swe.julday(2024, 1, 1, 12.0, ephemeris.swe.GREG_CAL)
        self.assertAlmostEqual(jd, expected, places=6)

    def test_to_julian_day_invalid_timezone(self) -> None:
        with self.assertRaises(ephemeris.AstroCalculationError):
            ephemeris.to_julian_day(date(2024, 1, 1), time(12, 0), "Mars/Phobos", 0.0, 0.0)

    @mock.patch("apps.astro.services.ephemeris.swe.houses_ex")
    @mock.patch("apps.astro.services.ephemeris.swe.calc_ut")
    def test_get_planet_positions_uses_swisseph(self, mock_calc_ut: mock.Mock, mock_houses: mock.Mock) -> None:
        def fake_calc(jd: float, planet_id: int, flags: int) -> tuple[float, float, float, float, float, float]:
            base = float(planet_id)
            return (base, 0.0, 0.0, base / 100.0, 0.0, 0.0)

        mock_calc_ut.side_effect = fake_calc
        mock_houses.return_value = ([0.0] * 12, [101.5, 202.5, 0, 0, 0, 0, 0, 0, 0, 0])

        positions = ephemeris.get_planet_positions(2457023.5, 37.7749, -122.4194)

        self.assertIn("sun", positions)
        self.assertIn("asc", positions)
        self.assertEqual(positions["asc"]["lon"], 101.5)
        self.assertAlmostEqual(positions["moon"]["speed"], ephemeris.swe.MOON / 100.0)
        self.assertEqual(mock_calc_ut.call_count, len(ephemeris.PLANET_MAP))
        mock_houses.assert_called_once()

    def test_get_planet_positions_raises_on_calc_failure(self) -> None:
        with mock.patch("apps.astro.services.ephemeris.swe.calc_ut", side_effect=RuntimeError("file not found")):
            with self.assertRaises(ephemeris.AstroCalculationError):
                ephemeris.get_planet_positions(2457023.5, 0.0, 0.0)

    def test_get_planet_positions_rejects_bad_coordinates(self) -> None:
        with self.assertRaises(ephemeris.AstroCalculationError):
            ephemeris.get_planet_positions(2457023.5, 95.0, 0.0)
