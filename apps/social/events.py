from __future__ import annotations

import logging

from django.utils import timezone

from apps.core.pubsub import publish_event
from apps.payments.serializers import GiftTypeSerializer
from apps.social.models import PaidReaction

logger = logging.getLogger(__name__)


def _format_timestamp(dt) -> str:
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_gift_received(*, reaction: PaidReaction, channel: str, request=None) -> None:
    try:
        gift_type_data = GiftTypeSerializer(reaction.gift_type, context={"request": request}).data
        target_type = reaction.target_type
        target_id = reaction.post_id if target_type == PaidReaction.TargetType.POST else reaction.comment_id
        payload = {
            "type": "gift.received",
            "id": reaction.id,
            "target": {"type": target_type, "id": target_id},
            "sender": {"id": reaction.sender_id},
            "gift_type": gift_type_data,
            "quantity": reaction.quantity,
            "total_amount_cents": reaction.total_amount_cents,
            "created_at": _format_timestamp(reaction.created_at),
        }
        publish_event(channel, payload)
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("gift_received publish failed channel=%s reaction_id=%s error=%s", channel, reaction.id, exc)
