from __future__ import annotations

from datetime import date, time
from unittest import mock

from rest_framework import status

from apps.astro.models import BirthData, NatalChart
from apps.users.models import User
from tests.test_api import BaseAPITestCase


def _seed_chart(user: User) -> NatalChart:
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
        planets={"sun": {"lon": 0.0, "sign": "Aries"}, "moon": {"lon": 15.0, "sign": "Aries"}},
        houses={"1": {"cusp_lon": 0.0, "sign": "Aries"}},
        aspects=[],
    )


class MentorAIApiTests(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.register_and_login(email="mentorai@example.com", handle="mentorai")
        self.other = User.objects.create_user(email="otherai@example.com", password="pass123", handle="otherai", name="Other AI")

    @mock.patch("apps.mentor.views.generate_llama_response", return_value="AI natal guidance")
    def test_natal_mentor_requires_chart(self, mock_llm) -> None:
        response = self.client.post("/api/v1/mentor/natal/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        _seed_chart(User.objects.get(id=self.user["id"]))
        response = self.client.post("/api/v1/mentor/natal/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("mentor_text", response.data)
        mock_llm.assert_called()

    @mock.patch("apps.mentor.views.generate_llama_response", return_value="Soulmatch guidance")
    @mock.patch("apps.mentor.views.calculate_soulmatch")
    def test_soulmatch_mentor_flow(self, mock_calc, mock_llm) -> None:
        mock_calc.return_value = {
            "user_id": self.other.id,
            "score": 75,
            "components": {"astro": 20, "matrix": 15, "psychology": 20, "lifestyle": 20},
            "tags": ["aligned_lifestyle"],
        }
        response = self.client.get(f"/api/v1/mentor/soulmatch/{self.other.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 75)
        self.assertIn("mentor_text", response.data)

    def test_soulmatch_mentor_blocks_self(self) -> None:
        response = self.client.get(f"/api/v1/mentor/soulmatch/{self.user['id']}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("apps.mentor.views.generate_llama_response", return_value="Point one\nPoint two")
    @mock.patch("apps.mentor.views.get_today_transits")
    def test_daily_mentor(self, mock_transits, mock_llm) -> None:
        mock_transits.return_value = {"sun_today": {"lon": 10, "sign": "Aries"}, "moon_today": {"lon": 20, "sign": "Aries"}}
        _seed_chart(User.objects.get(id=self.user["id"]))
        response = self.client.get("/api/v1/mentor/daily/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("messages", response.data)
        mock_llm.assert_called()
        mock_transits.assert_called()
