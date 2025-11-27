from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Set

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


def _is_within_quiet_hours(settings: UserSettings | None) -> bool:
    if not settings:
        return False
    quiet = settings.quiet_hours or {}
    start = quiet.get("start")
    end = quiet.get("end")
    if not start or not end:
        return False
    now = timezone.localtime()
    try:
        start_hour, start_minute = [int(part) for part in start.split(":")]
        end_hour, end_minute = [int(part) for part in end.split(":")]
    except (ValueError, AttributeError):
        return False
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    current_minutes = now.hour * 60 + now.minute
    if start_minutes <= end_minutes:
        return start_minutes <= current_minutes <= end_minutes
    return current_minutes >= start_minutes or current_minutes <= end_minutes


def send_push_notification(
    users: Iterable[User],
    payload: NotificationPayload,
    *,
    skip_user_ids: Iterable[int] | None = None,
) -> None:
    skipped: Set[int] = set(skip_user_ids or [])
    for user in users:
        if user.id in skipped:
            continue
        settings = getattr(user, "settings", None)
        if settings and (not settings.push_enabled or _is_within_quiet_hours(settings)):
            continue
        devices = getattr(user, "devices", None)
        device_list = list(devices.all()) if devices is not None else []
        for device in device_list:
            logger.info(
                "[push] Would send %s to %s via %s",
                payload.type,
                device.push_token,
                device.device_type,
            )


def send_email_notification(users: Iterable[User], payload: NotificationPayload) -> None:
    for user in users:
        settings = getattr(user, "settings", None)
        if settings and (not settings.email_enabled or _is_within_quiet_hours(settings)):
            continue
        logger.info("[email] Would send %s to %s", payload.type, user.email)


def dispatch_notification(
    users: Iterable[User],
    payload: NotificationPayload,
    *,
    send_push: bool = True,
    skip_push_user_ids: Iterable[int] | None = None,
) -> None:
    users = list(users)
    for user in users:
        create_in_app_notification(user, payload)
    if send_push:
        send_push_notification(users, payload, skip_user_ids=skip_push_user_ids)
    send_email_notification(users, payload)
