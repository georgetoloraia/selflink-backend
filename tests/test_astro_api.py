from __future__ import annotations

from datetime import date, time
from unittest import mock

from rest_framework import status

from tests.test_api import BaseAPITestCase


POST_PAYLOAD = {
    "date_of_birth": "1990-01-01",
    "time_of_birth": "12:00:00",
    "timezone": "UTC",
    "city": "San Francisco",
    "country": "USA",
    "latitude": 37.7749,
    "longitude": -122.4194,
}


class NatalChartAPITests(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.register_and_login(email="astro@example.com", handle="astro")

    @mock.patch("apps.astro.views.chart_calculator.calculate_natal_chart")
    def test_create_birth_data_and_chart(self, mock_calc: mock.Mock) -> None:
        mock_calc.return_value = self._fake_chart_response()

        response = self.client.post("/api/v1/astro/natal/", POST_PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("planets", response.data)
        self.assertIn("houses", response.data)
        self.assertIn("aspects", response.data)

    @mock.patch("apps.astro.views.chart_calculator.calculate_natal_chart")
    def test_update_existing_birth_data_returns_200(self, mock_calc: mock.Mock) -> None:
        mock_calc.return_value = self._fake_chart_response()
        self.client.post("/api/v1/astro/natal/", POST_PAYLOAD, format="json")

        updated = dict(POST_PAYLOAD)
        updated["city"] = "Oakland"
        response = self.client.post("/api/v1/astro/natal/", updated, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_calc.assert_called()

    def test_get_missing_chart_returns_404(self) -> None:
        response = self.client.get("/api/v1/astro/natal/me/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch("apps.astro.views.NatalChart.objects.get")
    def test_get_existing_chart(self, mock_get: mock.Mock) -> None:
        chart = self._fake_chart_response()
        mock_get.return_value = chart

        response = self.client.get("/api/v1/astro/natal/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["planets"]["sun"]["lon"], 0.0)

    def _fake_chart_response(self):
        from apps.astro.models import NatalChart, BirthData
        from apps.users.models import User

        user = User.objects.get(email="astro@example.com")
        birth_data, _ = BirthData.objects.get_or_create(
            user=user,
            defaults={
                "date_of_birth": date(1990, 1, 1),
                "time_of_birth": time(12, 0),
                "timezone": "UTC",
                "latitude": 37.7749,
                "longitude": -122.4194,
            },
        )
        return NatalChart(
            user=user,
            birth_data=birth_data,
            planets={"sun": {"lon": 0.0, "sign": "Aries"}},
            houses={"1": {"cusp_lon": 0.0, "sign": "Aries"}},
            aspects=[],
        )
