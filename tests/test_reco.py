from django.test import TestCase

from apps.mentor.models import MentorMemory
from apps.reco.models import SoulMatchProfile
from apps.reco.services import refresh_soulmatch_profile
from apps.users.models import User


class SoulMatchProfileTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="soul@example.com",
            handle="soul",
            name="Soul",
            password="password123",
        )

    def test_refresh_creates_profile(self) -> None:
        refresh_soulmatch_profile(self.user)
        profile = SoulMatchProfile.objects.get(user=self.user)
        self.assertEqual(profile.avg_sentiment, 0.0)
        self.assertEqual(profile.social_score, 0.0)

    def test_refresh_uses_memory(self) -> None:
        memory = MentorMemory.objects.create(user=self.user, notes={"entries": [{"sentiment": "positive"}]})
        profile = refresh_soulmatch_profile(self.user)
        self.assertGreater(profile.avg_sentiment, 0.0)
