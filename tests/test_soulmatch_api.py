from __future__ import annotations

from unittest import mock

from rest_framework import status

from apps.users.models import User
from tests.test_api import BaseAPITestCase


class SoulmatchAPITests(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.register_and_login(email="me@example.com", handle="me")
        self.other = User.objects.create_user(email="other@example.com", password="pass123", handle="other", name="Other")

    @mock.patch("apps.matching.views.calculate_soulmatch")
    def test_soulmatch_with_user(self, mock_calc) -> None:
        mock_calc.return_value = {
            "user_id": self.other.id,
            "score": 88,
            "components": {"astro": 30, "matrix": 15, "psychology": 30, "lifestyle": 13},
            "tags": ["soulmate_like"],
        }

        resp = self.client.get(f"/api/v1/soulmatch/with/{self.other.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["score"], 88)
        self.assertEqual(resp.data["user"]["id"], self.other.id)

    @mock.patch("apps.matching.tasks.soulmatch_compute_score_task.apply_async")
    def test_soulmatch_with_user_async_enqueues(self, mock_task) -> None:
        mock_task.return_value.id = "task-match-1"

        resp = self.client.get(f"/api/v1/soulmatch/with/{self.other.id}/?async=true")
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(resp.data["task_id"], "task-match-1")
        mock_task.assert_called_once()

    def test_soulmatch_with_self_returns_400(self) -> None:
        resp = self.client.get(f"/api/v1/soulmatch/with/{self.user['id']}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("apps.matching.views.calculate_soulmatch")
    def test_recommendations_excludes_self(self, mock_calc) -> None:
        User.objects.create_user(email="third@example.com", password="pass123", handle="third", name="Third")
        mock_calc.return_value = {
            "user_id": self.other.id,
            "score": 50,
            "components": {"astro": 15, "matrix": 15, "psychology": 10, "lifestyle": 10},
            "tags": ["neutral"],
        }

        resp = self.client.get("/api/v1/soulmatch/recommendations/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [item["user"]["id"] for item in resp.data]
        self.assertNotIn(self.user["id"], ids)
