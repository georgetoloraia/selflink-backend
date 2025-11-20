from __future__ import annotations

from rest_framework import status

from tests.test_api import BaseAPITestCase


class ProfileAPITests(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.register_and_login(email="profile@example.com", handle="profile")

    def test_get_without_profile_returns_404(self) -> None:
        response = self.client.get("/api/v1/profile/me/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_profile_on_patch(self) -> None:
        payload = {
            "gender": "female",
            "orientation": "bi",
            "relationship_goal": "casual",
            "values": ["growth", "freedom"],
            "preferred_lifestyle": ["remote_work"],
            "attachment_style": "secure",
            "love_language": ["words", "quality_time"],
        }
        response = self.client.patch("/api/v1/profile/me/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["gender"], "female")

    def test_update_profile(self) -> None:
        self.client.patch("/api/v1/profile/me/", {"gender": "male"}, format="json")
        response = self.client.patch("/api/v1/profile/me/", {"gender": "non_binary"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["gender"], "non_binary")

    def test_rejects_invalid_values_list(self) -> None:
        response = self.client.patch("/api/v1/profile/me/", {"values": "not-a-list"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
