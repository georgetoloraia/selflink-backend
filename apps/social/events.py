from __future__ import annotations

import logging

from django.utils import timezone

from apps.realtime.publish import publish_realtime_event
from apps.payments.serializers import GiftTypeSerializer
from apps.social.models import PaidReaction

logger = logging.getLogger(__name__)


def _format_timestamp(dt) -> str:
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_gift_received(*, reaction: PaidReaction, channel: str, request=None) -> None:
    try:
        request_id = ""
        if request is not None:
            request_id = request.META.get("HTTP_X_REQUEST_ID", "")
        gift_type_data = GiftTypeSerializer(reaction.gift_type, context={"request": request}).data
        price_slc = gift_type_data.get("price_slc_cents") or gift_type_data.get("price_cents")
        gift_type_payload = {
            "id": gift_type_data.get("id"),
            "key": gift_type_data.get("key"),
            "name": gift_type_data.get("name"),
            "kind": gift_type_data.get("kind"),
            "media_url": gift_type_data.get("media_url") or "",
            "animation_url": gift_type_data.get("animation_url") or "",
            "price_slc_cents": price_slc,
            "is_active": gift_type_data.get("is_active", True),
        }
        target_type = reaction.target_type
        target_id = reaction.post_id if target_type == PaidReaction.TargetType.POST else reaction.comment_id
        payload = {
            "type": "gift.received",
            "id": reaction.id,
            "target": {"type": target_type, "id": target_id},
            "sender": {"id": reaction.sender_id},
            "gift_type": gift_type_payload,
            "quantity": reaction.quantity,
            "total_amount_cents": reaction.total_amount_cents,
            "created_at": _format_timestamp(reaction.created_at),
        }
        context = {
            "event_id": reaction.id,
            "target_type": target_type,
            "target_id": target_id,
            "sender_id": reaction.sender_id,
            "request_id": request_id,
        }
        publish_realtime_event(channel, payload, context=context)
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("gift_received publish failed channel=%s reaction_id=%s error=%s", channel, reaction.id, exc)
