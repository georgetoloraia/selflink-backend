from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.search.tasks import delete_post_task, delete_user_task, index_post_task, index_user_task
from apps.social.models import Post
from apps.users.models import User


@receiver(post_save, sender=User)
def trigger_user_index(sender, instance: User, **kwargs) -> None:
    index_user_task.delay(instance.id)


@receiver(post_delete, sender=User)
def trigger_user_delete(sender, instance: User, **kwargs) -> None:
    delete_user_task.delay(instance.id)


@receiver(post_save, sender=Post)
def trigger_post_index(sender, instance: Post, **kwargs) -> None:
    index_post_task.delay(instance.id)


@receiver(post_delete, sender=Post)
def trigger_post_delete(sender, instance: Post, **kwargs) -> None:
    delete_post_task.delay(instance.id)
