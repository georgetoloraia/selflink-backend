from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.payments.models import Wallet

from .models import User, UserSettings


@receiver(post_save, sender=User)
def create_related_user_models(sender, instance: User, created: bool, **kwargs) -> None:
    if created:
        UserSettings.objects.get_or_create(user=instance)
        Wallet.objects.get_or_create(user=instance)
