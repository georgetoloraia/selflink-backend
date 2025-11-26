from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.feed.rank import (
    FEED_RANKING_CONFIG_FOR_YOU,
    FEED_RANKING_CONFIG_FOR_YOU_VIDEOS,
    compute_engagement_score,
    compute_recency_score,
    score_post_for_user,
)
from apps.social.models import Follow, Post
from apps.users.models import User


class RankingSignalTests(TestCase):
    def test_compute_recency_score_prefers_recent_posts(self) -> None:
        author = User.objects.create_user(
            email="recency@example.com",
            handle="recent_author",
            name="Recency Author",
            password="strongpassword",
        )
        recent = Post.objects.create(author=author, text="Recent post")
        older = Post.objects.create(author=author, text="Older post")
        Post.objects.filter(id=older.id).update(created_at=timezone.now() - timedelta(days=2))
        older.refresh_from_db()

        recent_score = compute_recency_score(recent)
        older_score = compute_recency_score(older)

        self.assertGreater(recent_score, older_score)
        self.assertGreater(recent_score, 0.0)

    def test_compute_engagement_score_is_bounded_and_monotonic(self) -> None:
        author = User.objects.create_user(
            email="engagement@example.com",
            handle="engager",
            name="Engager",
            password="strongpassword",
        )
        low = Post(author=author, text="Low engagement", like_count=1, comment_count=0)
        mid = Post(author=author, text="Mid engagement", like_count=10, comment_count=3)
        high = Post(author=author, text="High engagement", like_count=80, comment_count=20)

        low_like, low_comment = compute_engagement_score(low)
        mid_like, mid_comment = compute_engagement_score(mid)
        high_like, high_comment = compute_engagement_score(high)

        self.assertGreater(mid_like, low_like)
        self.assertGreater(high_like, mid_like)
        self.assertLess(high_like, 1.01)

        self.assertGreater(mid_comment, low_comment)
        self.assertGreater(high_comment, mid_comment)
        self.assertLess(high_comment, 1.01)


class ScorePostConfigTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="viewer@example.com",
            handle="viewer",
            name="Viewer",
            password="strongpassword",
        )
        self.followee = User.objects.create_user(
            email="followed@example.com",
            handle="followed",
            name="Followed",
            password="strongpassword",
        )
        self.other = User.objects.create_user(
            email="other@example.com",
            handle="other",
            name="Other",
            password="strongpassword",
        )

    def test_for_you_config_prioritizes_follow_and_engagement(self) -> None:
        Follow.objects.create(follower=self.user, followee=self.followee)
        followee_post = Post.objects.create(author=self.followee, text="Followed author post")
        other_post = Post.objects.create(author=self.other, text="Stranger post")
        Post.objects.filter(id=followee_post.id).update(
            like_count=12,
            comment_count=4,
            created_at=timezone.now() - timedelta(hours=2),
        )
        Post.objects.filter(id=other_post.id).update(
            like_count=1,
            comment_count=0,
            created_at=timezone.now() - timedelta(hours=1),
        )
        followee_post.refresh_from_db()
        other_post.refresh_from_db()
        followee_ids = {self.followee.id}

        score_followed = score_post_for_user(
            self.user, followee_post, FEED_RANKING_CONFIG_FOR_YOU, followee_ids=followee_ids
        )
        score_other = score_post_for_user(
            self.user, other_post, FEED_RANKING_CONFIG_FOR_YOU, followee_ids=followee_ids
        )

        self.assertGreater(score_followed, score_other)

    def test_video_config_rewards_video_posts(self) -> None:
        video_post = Post.objects.create(author=self.other, text="Video post", like_count=4, comment_count=2)
        plain_post = Post.objects.create(author=self.other, text="Plain post", like_count=4, comment_count=2)

        aligned_time = timezone.now() - timedelta(hours=1)
        Post.objects.filter(id__in=[video_post.id, plain_post.id]).update(created_at=aligned_time)
        video_post.refresh_from_db()
        plain_post.refresh_from_db()
        video_post.video = object()

        score_video = score_post_for_user(
            self.user,
            video_post,
            FEED_RANKING_CONFIG_FOR_YOU_VIDEOS,
            followee_ids=set(),
        )
        score_plain = score_post_for_user(
            self.user,
            plain_post,
            FEED_RANKING_CONFIG_FOR_YOU_VIDEOS,
            followee_ids=set(),
        )

        self.assertGreater(score_video, score_plain)
