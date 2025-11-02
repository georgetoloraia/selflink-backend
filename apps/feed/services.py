from __future__ import annotations

from typing import Iterable

from django.db import transaction

from apps.social.models import Follow, Post, Timeline


def fan_out_post(post: Post) -> None:
    followers = Follow.objects.filter(followee=post.author).values_list("follower_id", flat=True)
    _bulk_timeline_entries(post, followers)
    Timeline.objects.update_or_create(user=post.author, post=post, defaults={"score": 1.0})


def _bulk_timeline_entries(post: Post, user_ids: Iterable[int]) -> None:
    with transaction.atomic():
        entries = [
            Timeline(user_id=user_id, post=post, score=1.0)
            for user_id in user_ids
        ]
        Timeline.objects.bulk_create(entries, ignore_conflicts=True)
