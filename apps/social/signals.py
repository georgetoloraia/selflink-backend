from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.feed.services.cache import FeedCache
from apps.feed.services import fan_out_post

from .models import Post


@receiver(post_save, sender=Post)
def handle_post_created(sender, instance: Post, created: bool, **kwargs) -> None:
    if created:
        fan_out_post(instance)
        FeedCache.invalidate_first_page(instance.author_id)
