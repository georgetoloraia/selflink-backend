from __future__ import annotations

import os

from rest_framework import status
from rest_framework.test import APITestCase

from apps.mentor.models import MentorMemory
from apps.social.models import Post, Timeline
from apps.users.models import User


class BaseAPITestCase(APITestCase):
    def register_and_login(self, email: str = "test@example.com", handle: str = "tester") -> dict:
        register_payload = {
            "email": email,
            "handle": handle,
            "name": "Test User",
            "password": "strongpassword",
        }
        response = self.client.post("/api/v1/auth/register/", register_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"email": email, "password": register_payload["password"]},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return login_response.data["user"]


class AuthTests(BaseAPITestCase):
    def test_register_and_login_returns_tokens(self) -> None:
        user = self.register_and_login()
        self.assertEqual(user["handle"], "tester")


class PostTests(BaseAPITestCase):
    def test_create_and_like_post(self) -> None:
        self.register_and_login(email="poster@example.com", handle="poster")
        payload = {"text": "Hello SelfLink", "visibility": "public"}
        response = self.client.post("/api/v1/posts/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_id = response.data["id"]

        like_response = self.client.post(f"/api/v1/posts/{post_id}/like/")
        self.assertEqual(like_response.status_code, status.HTTP_200_OK)
        self.assertTrue(like_response.data["liked"])


class MentorTests(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        os.environ["MENTOR_LLM_ENABLED"] = "false"

    def test_mentor_ask_returns_answer(self) -> None:
        self.register_and_login(email="mentor@example.com", handle="seek")
        question = {"text": "I feel anxious today"}
        response = self.client.post("/api/v1/mentor/sessions/ask/", question, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("answer", response.data)
        self.assertIn("sentiment", response.data)

    def test_mentor_memory_persists(self) -> None:
        user = self.register_and_login(email="memory@example.com", handle="memory")
        self.client.post("/api/v1/mentor/sessions/ask/", {"text": "Feeling optimistic today"}, format="json")
        self.client.post("/api/v1/mentor/sessions/ask/", {"text": "A bit tired now"}, format="json")
        memory = MentorMemory.objects.get(user_id=user["id"])
        entries = memory.notes.get("entries", [])
        self.assertGreaterEqual(len(entries), 2)
        self.assertTrue(memory.last_summary)


class FollowTimelineTests(BaseAPITestCase):
    def test_follow_populates_timeline(self) -> None:
        follower = self.register_and_login(email="timeline@example.com", handle="timeline")
        followee = User.objects.create_user(
            email="followee@example.com",
            handle="followee",
            name="Followee",
            password="strongpassword",
        )
        Post.objects.create(author=followee, text="A mindful connection moment.")

        response = self.client.post(f"/api/v1/users/{followee.id}/follow/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        feed = self.client.get("/api/v1/feed/home/")
        self.assertEqual(feed.status_code, status.HTTP_200_OK)
        results = feed.data.get("results") if isinstance(feed.data, dict) else feed.data
        self.assertTrue(results)

    def test_unfollow_clears_timeline(self) -> None:
        follower = self.register_and_login(email="unfollow@example.com", handle="unfollow")
        followee = User.objects.create_user(
            email="followed@example.com",
            handle="followed",
            name="Followed",
            password="strongpassword",
        )
        post = Post.objects.create(author=followee, text="Presence and gratitude.")
        self.client.post(f"/api/v1/users/{followee.id}/follow/")
        self.client.delete(f"/api/v1/users/{followee.id}/follow/")

        feed = self.client.get("/api/v1/feed/home/")
        self.assertEqual(feed.status_code, status.HTTP_200_OK)
        results = feed.data.get("results") if isinstance(feed.data, dict) else feed.data
        self.assertFalse(results)
        self.assertFalse(Timeline.objects.filter(user_id=follower["id"], post=post).exists())
