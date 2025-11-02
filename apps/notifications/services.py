from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from django.utils import timezone

from apps.notifications.models import Notification
from apps.users.models import User, UserSettings

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    type: str
    payload: dict


def create_in_app_notification(user: User, payload: NotificationPayload) -> Notification:
    notification = Notification.objects.create(
        user=user,
        type=payload.type,
        payload=payload.payload,
    )
    return notification


def send_push_notification(users: Iterable[User], payload: NotificationPayload) -> None:
    for user in users:
        settings = getattr(user, "settings", None)
        if settings and not settings.flags.get("push_enabled", True):
            continue
        logger.info("[push] Would send %s to %s", payload.type, user.id)


def send_email_notification(users: Iterable[User], payload: NotificationPayload) -> None:
    for user in users:
        logger.info("[email] Would send %s to %s", payload.type, user.email)


def dispatch_notification(users: Iterable[User], payload: NotificationPayload) -> None:
    users = list(users)
    for user in users:
        create_in_app_notification(user, payload)
    send_push_notification(users, payload)
    send_email_notification(users, payload)
