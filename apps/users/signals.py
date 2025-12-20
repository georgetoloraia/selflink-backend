from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.payments.models import Wallet
from apps.profile.models import UserProfile

from .models import User, UserPII, UserSettings


@receiver(post_save, sender=User)
def create_related_user_models(sender, instance: User, created: bool, **kwargs) -> None:
    if created:
        UserSettings.objects.get_or_create(user=instance)
        Wallet.objects.get_or_create(user=instance)
        UserProfile.objects.get_or_create(user=instance)
    UserPII.objects.update_or_create(
        user=instance,
        defaults={
            "full_name": instance.name or "",
            "email": instance.email or "",
            "birth_date": instance.birth_date,
            "birth_time": instance.birth_time,
            "birth_place": instance.birth_place or "",
        },
    )
