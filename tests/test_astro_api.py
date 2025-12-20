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

    @mock.patch("apps.astro.tasks.astrology_compute_birth_chart_task.apply_async")
    def test_async_chart_enqueue(self, mock_task: mock.Mock) -> None:
        mock_task.return_value.id = "task-astro-1"

        response = self.client.post("/api/v1/astro/natal/?async=true", POST_PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["task_id"], "task-astro-1")
        mock_task.assert_called_once()

    @mock.patch("apps.astro.services.location_resolver.resolve_timezone_from_coordinates", return_value="Etc/GMT")
    @mock.patch("apps.astro.views.chart_calculator.calculate_natal_chart")
    def test_coordinates_override_city_country(self, mock_calc: mock.Mock, mock_tz: mock.Mock) -> None:
        mock_calc.return_value = self._fake_chart_response()

        payload = dict(POST_PAYLOAD)
        payload["city"] = "Nowhere"
        payload["country"] = "Nowhere"
        payload.pop("timezone", None)

        response = self.client.post("/api/v1/astro/natal/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        from apps.astro.models import BirthData

        birth = BirthData.objects.get(user__email="astro@example.com")
        self.assertEqual(birth.latitude, payload["latitude"])
        self.assertEqual(birth.longitude, payload["longitude"])
        self.assertEqual(birth.timezone, "Etc/GMT")
        mock_tz.assert_called_once()

    def test_invalid_coordinates_return_400(self) -> None:
        bad_payload = dict(POST_PAYLOAD)
        bad_payload["latitude"] = 123.0

        response = self.client.post("/api/v1/astro/natal/", bad_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("latitude", response.data)

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
        birth_data = BirthData(
            user=user,
            date_of_birth=date(1990, 1, 1),
            time_of_birth=time(12, 0),
            timezone="UTC",
            latitude=37.7749,
            longitude=-122.4194,
        )
        return NatalChart(
            user=user,
            birth_data=birth_data,
            planets={"sun": {"lon": 0.0, "sign": "Aries"}},
            houses={"1": {"cusp_lon": 0.0, "sign": "Aries"}},
            aspects=[],
        )
