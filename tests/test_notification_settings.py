from django.test import TestCase

from apps.users.models import User, UserSettings


class NotificationSettingTests(TestCase):
    def test_defaults_created(self):
        user = User.objects.create_user(email="notify@example.com", handle="notify", name="Notify", password="pass12345")
        settings = UserSettings.objects.get(user=user)
        self.assertTrue(settings.push_enabled)
        self.assertTrue(settings.email_enabled)
        self.assertFalse(settings.digest_enabled)
