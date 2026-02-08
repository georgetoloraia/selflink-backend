from __future__ import annotations

import logging
from datetime import UTC, timedelta

from django.utils import timezone

from apps.payments.serializers import GiftTypeSerializer
from apps.realtime.publish import publish_realtime_event
from apps.social.models import PaidReaction

logger = logging.getLogger(__name__)


def _format_timestamp(dt) -> str:
    """
    Format an aware datetime as RFC3339 / ISO8601 with Z suffix.
    Returns empty string for falsy dt.
    """
    if not dt:
        return ""
    # Ensure UTC and emit Z instead of +00:00
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def publish_gift_received(*, reaction: PaidReaction, channel: str, request=None) -> None:
    """
    Best-effort realtime publish for gift.received events.

    Does NOT raise; failures are logged and the caller continues (gift spend
    already persisted).
    """
    try:
        request_id = ""
        if request is not None:
            request_id = request.META.get("HTTP_X_REQUEST_ID", "") or ""

        gift_type_payload = GiftTypeSerializer(reaction.gift_type, context={"request": request}).data

        # Back-compat: some clients read price_slc_cents; if missing, mirror price_cents.
        price_slc = gift_type_payload.get("price_slc_cents") or gift_type_payload.get("price_cents")
        gift_type_payload["price_slc_cents"] = price_slc

        target_type = reaction.target_type
        target_id = reaction.post_id if target_type == PaidReaction.TargetType.POST else reaction.comment_id

        server_time = timezone.now()

        payload = {
            "type": "gift.received",
            "id": reaction.id,
            "target": {"type": target_type, "id": target_id},
            "sender": {"id": reaction.sender_id},
            "gift_type": gift_type_payload,
            "quantity": reaction.quantity,
            "total_amount_cents": reaction.total_amount_cents,
            "created_at": _format_timestamp(reaction.created_at),
            "server_time": _format_timestamp(server_time),
        }

        # Optional: expires_at (Effects v2 persist window)
        effects = gift_type_payload.get("effects") or {}
        persist = effects.get("persist") if isinstance(effects, dict) else {}
        if isinstance(persist, dict) and persist.get("mode") == "window":
            try:
                window_seconds = int(persist.get("window_seconds") or 0)
            except (TypeError, ValueError):
                window_seconds = 0
            if window_seconds > 0:
                expires_at = server_time + timedelta(seconds=window_seconds)
                payload["expires_at"] = _format_timestamp(expires_at)

        context = {
            "event_id": reaction.id,
            "target_type": target_type,
            "target_id": target_id,
            "sender_id": reaction.sender_id,
            "request_id": request_id,
        }

        publish_realtime_event(channel, payload, context=context)

    except Exception as exc:  # pragma: no cover - best effort
        logger.warning(
            "gift_received publish failed channel=%s reaction_id=%s error=%s",
            channel,
            getattr(reaction, "id", None),
            exc,
        )
