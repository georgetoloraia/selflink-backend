from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from apps.moderation.autoflag import auto_report_message, auto_report_post
from apps.moderation.permissions import IsModerationStaff
from apps.moderation.models import Report, ReportTargetType, ReportStatus
from apps.messaging.models import Message, Thread, ThreadMember
from apps.social.models import Post
from apps.users.models import User


class ModerationTests(TestCase):
    def setUp(self) -> None:
        self.staff_group = Group.objects.create(name="moderation_team")
        self.permission = IsModerationStaff()

    def test_permission_for_group_member(self):
        user = User.objects.create_user(email="mod@example.com", handle="mod", name="Mod", password="pass12345")
        user.groups.add(self.staff_group)
        request = type("obj", (), {"user": user})
        self.assertTrue(self.permission.has_permission(request, None))

    def test_report_status_choices(self):
        statuses = ReportStatus.values
        self.assertIn("open", statuses)
        self.assertIn("resolved", statuses)

    @override_settings(MODERATION_BANNED_WORDS=["banned"])
    def test_auto_report_message(self):
        user = User.objects.create_user(email="msg@example.com", handle="msg", name="Msg", password="pass12345")
        thread = Thread.objects.create(created_by=user)
        ThreadMember.objects.create(thread=thread, user=user)
        message = Message.objects.create(thread=thread, sender=user, body="contains banned content")
        auto_report_message(message)
        self.assertTrue(Report.objects.filter(target_type=ReportTargetType.MESSAGE, target_id=message.id).exists())

    @override_settings(MODERATION_BANNED_WORDS=["banned"])
    def test_auto_report_post(self):
        user = User.objects.create_user(email="post@example.com", handle="post", name="Post", password="pass12345")
        post = Post.objects.create(author=user, text="banned words here")
        auto_report_post(post)
        self.assertTrue(Report.objects.filter(target_type=ReportTargetType.POST, target_id=post.id).exists())
