from django.test import TestCase

from apps.config.models import FeatureFlag
from apps.config.services import is_enabled


class FeatureFlagTests(TestCase):
    def test_feature_flag_toggle(self) -> None:
        FeatureFlag.objects.create(key="experiment", description="", enabled=False)
        self.assertFalse(is_enabled("experiment"))

        flag = FeatureFlag.objects.get(key="experiment")
        flag.enabled = True
        flag.rollout = 0
        flag.save()
        self.assertTrue(is_enabled("experiment"))

    def test_feature_flag_rollout_bucket(self) -> None:
        FeatureFlag.objects.create(key="percent_flag", enabled=True, rollout=50)
        self.assertTrue(is_enabled("percent_flag", user_id=10))
        self.assertFalse(is_enabled("percent_flag", user_id=90))
