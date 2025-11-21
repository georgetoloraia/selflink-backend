from __future__ import annotations

from datetime import date, time
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from apps.profile.models import UserProfile
from apps.users.models import User


class AstroProfileSourceTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="astroprofile@example.com",
            password="pass1234",
            handle="astroprofile",
            name="Astro Profile",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._login_token()}")

    def _login_token(self) -> str:
        response = self.client.post(
            "/api/v1/auth/login",
            {"email": "astroprofile@example.com", "password": "pass1234"},
            format="json",
        )
        return response.data["token"]

    def test_profile_source_success_with_existing_timezone(self) -> None:
        profile = UserProfile.objects.get(user=self.user)
        profile.birth_date = date(1990, 1, 1)
        profile.birth_time = time(12, 0)
        profile.birth_city = "Tbilisi"
        profile.birth_country = "Georgia"
        profile.birth_timezone = "Asia/Tbilisi"
        profile.birth_latitude = 41.7167
        profile.birth_longitude = 44.7833
        profile.save()

        response = self.client.post("/api/v1/astro/natal/", {"source": "profile"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("planets", response.data)

    def test_profile_source_resolves_location(self) -> None:
        profile = UserProfile.objects.get(user=self.user)
        profile.birth_date = date(1990, 1, 1)
        profile.birth_time = time(12, 0)
        profile.birth_city = "Tbilisi"
        profile.birth_country = "Georgia"
        profile.save()

        with mock.patch(
            "apps.astro.services.location_resolver.resolve_location_from_profile",
            return_value=mock.Mock(timezone="Asia/Tbilisi", latitude=41.7, longitude=44.7),
        ):
            response = self.client.post("/api/v1/astro/natal/", {"source": "profile"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_profile_source_missing_fields_returns_400(self) -> None:
        response = self.client.post("/api/v1/astro/natal/", {"source": "profile"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_profile_source_resolution_failure_returns_400(self) -> None:
        profile = UserProfile.objects.get(user=self.user)
        profile.birth_date = date(1990, 1, 1)
        profile.birth_time = time(12, 0)
        profile.birth_city = "Nowhere"
        profile.birth_country = "Nowhere"
        profile.save()

        with mock.patch(
            "apps.astro.services.location_resolver.resolve_location_from_profile",
            side_effect=Exception("fail"),
        ):
            response = self.client.post("/api/v1/astro/natal/", {"source": "profile"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
