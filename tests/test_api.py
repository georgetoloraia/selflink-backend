from __future__ import annotations

import os

from datetime import timedelta

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.feed.services.cache import FeedCache
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
        response = self.client.post("/api/v1/auth/register", register_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertIn("refreshToken", response.data)

        login_response = self.client.post(
            "/api/v1/auth/login",
            {"email": email, "password": register_payload["password"]},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return login_response.data["user"]


class AuthTests(BaseAPITestCase):
    def test_register_and_login_returns_tokens(self) -> None:
        user = self.register_and_login()
        self.assertEqual(user["handle"], "tester")

    def test_login_payload_contains_tokens_and_user(self) -> None:
        email = "payload@example.com"
        handle = "payload"
        password = "strongpassword"
        self.client.post(
            "/api/v1/auth/register",
            {"email": email, "handle": handle, "name": "Payload User", "password": password},
            format="json",
        )
        response = self.client.post(
            "/api/v1/auth/login",
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], email)
        self.assertIn("token", response.data)
        self.assertIn("refreshToken", response.data)

    def test_register_accepts_full_name_and_generates_handle(self) -> None:
        payload = {
            "email": "george@example.com",
            "password": "strongpassword",
            "fullName": "George Example",
            "intention": "Just exploring",
        }
        response = self.client.post("/api/v1/auth/register", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = response.data["user"]
        self.assertEqual(user["email"], payload["email"])
        self.assertEqual(user["name"], payload["fullName"])
        self.assertTrue(user["handle"])
        self.assertNotIn(" ", user["handle"])


class HomeHighlightsTests(APITestCase):
    def test_home_highlights_returns_expected_sections(self) -> None:
        response = self.client.get("/api/v1/home/highlights")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("hero", response.data)
        self.assertIn("features", response.data)
        self.assertIn("celebration", response.data)


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

    def test_create_post_with_video(self) -> None:
        self.register_and_login(email="videoposter@example.com", handle="videoposter")
        video_file = SimpleUploadedFile(
            "clip.mp4",
            b"fake video content",
            content_type="video/mp4",
        )
        payload = {"text": "Video upload", "video": video_file}
        response = self.client.post("/api/v1/posts/", payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        video = response.data.get("video")
        self.assertIsNotNone(video)
        self.assertTrue(video.get("url"))
        self.assertEqual(video.get("mime_type"), "video/mp4")
        self.assertIsNone(video.get("thumbnail_url"))

    def test_feed_includes_video_metadata(self) -> None:
        user_data = self.register_and_login(email="videofeed@example.com", handle="videofeed")
        video_file = SimpleUploadedFile(
            "feedclip.mp4",
            b"fake video content",
            content_type="video/mp4",
        )
        create_response = self.client.post(
            "/api/v1/posts/",
            {"text": "Video in feed", "video": video_file},
            format="multipart",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        feed = self.client.get("/api/v1/feed/home/")
        self.assertEqual(feed.status_code, status.HTTP_200_OK)
        items = feed.data.get("items", [])
        video_posts = [item for item in items if item.get("type") == "post" and item["post"].get("video")]
        self.assertTrue(video_posts)
        video = video_posts[0]["post"]["video"]
        self.assertTrue(video.get("url"))
        self.assertIsNone(video.get("thumbnail_url"))


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
        self.assertIn("items", feed.data)
        self.assertIn("next", feed.data)
        items = feed.data["items"]
        self.assertTrue(items)
        post_items = [item for item in items if item.get("type") == "post"]
        self.assertTrue(post_items)
        self.assertTrue(all("post" in item for item in post_items))

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
        self.assertIn("items", feed.data)
        self.assertEqual(feed.data["items"], [])
        self.assertIsNone(feed.data["next"])
        self.assertFalse(Timeline.objects.filter(user_id=follower["id"], post=post).exists())


class FeedResponseTests(BaseAPITestCase):
    def test_feed_returns_typed_items_and_insights(self) -> None:
        user_data = self.register_and_login(email="feed@example.com", handle="feed")
        user = User.objects.get(id=user_data["id"])
        for i in range(6):
            Post.objects.create(author=user, text=f"Post {i}")

        response = self.client.get("/api/v1/feed/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        item_types = {item.get("type") for item in items}
        self.assertIn("post", item_types)
        self.assertIn("mentor_insight", item_types)
        self.assertIn("matrix_insight", item_types)
        self.assertIn("soulmatch_reco", item_types)

        post_items = [item for item in items if item.get("type") == "post"]
        self.assertEqual(len(post_items), 6)
        self.assertTrue(all("post" in item for item in post_items))

        mentor_items = [item for item in items if item.get("type") == "mentor_insight"]
        matrix_items = [item for item in items if item.get("type") == "matrix_insight"]
        self.assertTrue(mentor_items)
        self.assertTrue(matrix_items)
        for m_item in mentor_items:
            mentor = m_item.get("mentor") or {}
            self.assertIn("title", mentor)
            self.assertIn("subtitle", mentor)
            self.assertIn("cta", mentor)
        for mx_item in matrix_items:
            matrix = mx_item.get("matrix") or {}
            self.assertIn("title", matrix)
            self.assertIn("subtitle", matrix)
            self.assertIn("cta", matrix)
        soulmatch_items = [item for item in items if item.get("type") == "soulmatch_reco"]
        self.assertTrue(soulmatch_items)
        for sm_item in soulmatch_items:
            soulmatch = sm_item.get("soulmatch") or {}
            self.assertIn("title", soulmatch)
            self.assertIn("subtitle", soulmatch)
            self.assertIn("cta", soulmatch)
            self.assertIn("profiles", soulmatch)

        self.assertIsNone(response.data["next"])

    def test_feed_paginates_and_returns_cursor(self) -> None:
        user_data = self.register_and_login(email="paginate@example.com", handle="paginate")
        user = User.objects.get(id=user_data["id"])
        for i in range(5):
            Post.objects.create(author=user, text=f"Pageable {i}")

        first_page = self.client.get("/api/v1/feed/home/?page_size=2")
        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertIn("items", first_page.data)
        cursor = first_page.data["next"]
        self.assertTrue(cursor)

        second_page = self.client.get(f"/api/v1/feed/home/?page_size=2&cursor={cursor}")
        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertIn("items", second_page.data)
        self.assertTrue(second_page.data["items"])


class FeedModeTests(BaseAPITestCase):
    def test_for_you_ranks_followed_and_engaged_posts(self) -> None:
        user = self.register_and_login(email="foryou@example.com", handle="foryou")
        followee = User.objects.create_user(
            email="followee@example.com",
            handle="followee",
            name="Followee",
            password="strongpassword",
        )
        other = User.objects.create_user(
            email="other@example.com",
            handle="otheruser",
            name="Other",
            password="strongpassword",
        )
        post_followee = Post.objects.create(author=followee, text="Followee post")
        post_other = Post.objects.create(author=other, text="Other post")

        Post.objects.filter(id=post_followee.id).update(
            like_count=10,
            comment_count=3,
            created_at=timezone.now() - timedelta(hours=2),
        )
        Post.objects.filter(id=post_other.id).update(
            like_count=0,
            comment_count=0,
            created_at=timezone.now() - timedelta(hours=1),
        )

        # follow followee to boost relationship signal
        self.client.post(f"/api/v1/users/{followee.id}/follow/")

        response = self.client.get("/api/v1/feed/for_you/?limit=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        post_items = [item for item in items if item.get("type") == "post"]
        self.assertTrue(post_items)
        top_post_id = post_items[0]["post"]["id"]
        self.assertEqual(top_post_id, post_followee.id)

    def test_following_feed_shows_only_followed_posts(self) -> None:
        user = self.register_and_login(email="followmode@example.com", handle="followmode")
        followee = User.objects.create_user(
            email="followee2@example.com",
            handle="followee2",
            name="Followee2",
            password="strongpassword",
        )
        other = User.objects.create_user(
            email="other2@example.com",
            handle="other2",
            name="Other2",
            password="strongpassword",
        )
        post_followee = Post.objects.create(author=followee, text="Followee timeline post")
        Post.objects.create(author=other, text="Other timeline post")

        self.client.post(f"/api/v1/users/{followee.id}/follow/")

        response = self.client.get("/api/v1/feed/following/?limit=5")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        post_items = [item for item in items if item.get("type") == "post"]
        self.assertTrue(post_items)
        self.assertTrue(all(p["post"]["id"] == post_followee.id for p in post_items))


class ForYouVideosFeedTests(BaseAPITestCase):
    def test_requires_authentication(self) -> None:
        response = self.client.get("/api/v1/feed/for_you_videos/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_video_feed_returns_only_video_posts(self) -> None:
        user = self.register_and_login(email="videomode@example.com", handle="videomode")
        # create one video post
        video_file = SimpleUploadedFile(
            "videomode.mp4",
            b"video content",
            content_type="video/mp4",
        )
        video_response = self.client.post(
            "/api/v1/posts/",
            {"text": "Video only", "video": video_file},
            format="multipart",
        )
        self.assertEqual(video_response.status_code, status.HTTP_201_CREATED)
        video_post_id = video_response.data["id"]

        # create a non-video post that should not appear
        non_video = self.client.post("/api/v1/posts/", {"text": "No video here"}, format="json")
        self.assertEqual(non_video.status_code, status.HTTP_201_CREATED)

        feed = self.client.get("/api/v1/feed/for_you_videos/")
        self.assertEqual(feed.status_code, status.HTTP_200_OK)
        items = feed.data.get("items", [])
        self.assertTrue(items)
        self.assertTrue(all(item.get("type") == "post" for item in items))
        self.assertTrue(all(item["post"].get("video") for item in items))
        ids = {item["post"]["id"] for item in items}
        self.assertIn(video_post_id, ids)
        self.assertNotIn(non_video.data["id"], ids)

    def test_video_feed_paginates_with_cursor(self) -> None:
        user = self.register_and_login(email="videopage@example.com", handle="videopage")
        for i in range(3):
            clip = SimpleUploadedFile(
                f"paginated_{i}.mp4",
                b"content",
                content_type="video/mp4",
            )
            response = self.client.post(
                "/api/v1/posts/",
                {"text": f"Video {i}", "video": clip},
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        first_page = self.client.get("/api/v1/feed/for_you_videos/?limit=1")
        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(first_page.data.get("items", [])), 1)
        cursor = first_page.data.get("next")
        self.assertIsNotNone(cursor)

        second_page = self.client.get(f"/api/v1/feed/for_you_videos/?limit=1&cursor={cursor}")
        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page.data.get("items", [])), 1)


class FeedCacheTests(BaseAPITestCase):
    def test_feed_cache_hit_returns_cached_payload(self) -> None:
        user = self.register_and_login(email="cache@example.com", handle="cache")
        payload = {"items": [{"type": "post", "id": 123, "post": {"id": 123}}], "next": None}
        FeedCache.set(user["id"], "for_you", None, payload)

        response = self.client.get("/api/v1/feed/for_you/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, payload)

    def test_like_invalidation_clears_first_page_cache(self) -> None:
        liker = self.register_and_login(email="liker@example.com", handle="liker")
        author = User.objects.create_user(
            email="author@example.com",
            handle="author",
            name="Author",
            password="strongpassword",
        )
        post = Post.objects.create(author=author, text="like me")

        payload = {"items": [], "next": None}
        FeedCache.set(liker["id"], "for_you", None, payload)
        FeedCache.set(author.id, "for_you", None, payload)

        response = self.client.post(f"/api/v1/posts/{post.id}/like/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(FeedCache.get(liker["id"], "for_you", None))
        self.assertIsNone(FeedCache.get(author.id, "for_you", None))

    def test_insight_uses_precomputed_cache(self) -> None:
        user = self.register_and_login(email="insightcache@example.com", handle="insightcache")
        today = timezone.localdate().isoformat()
        cached_payload = {
            "title": "Cached mentor",
            "subtitle": "Precomputed mentor insight",
            "cta": "Open mentor",
        }
        cache.set(f"mentor_insight:{user['id']}:{today}", cached_payload, 300)

        response = self.client.get("/api/v1/feed/for_you/?limit=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        mentor_items = [item for item in items if item.get("type") == "mentor_insight"]
        self.assertTrue(mentor_items)
        self.assertEqual(mentor_items[0]["mentor"], cached_payload)
