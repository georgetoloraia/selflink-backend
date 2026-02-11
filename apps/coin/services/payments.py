from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.coin.services.ledger import mint_for_payment
from apps.payments.models import PaymentEvent, PaymentEventStatus


def mint_from_payment_event(
    *,
    payment_event: PaymentEvent | None = None,
    payment_event_id: int | None = None,
    metadata: dict | None = None,
):
    if payment_event is None and payment_event_id is None:
        raise ValidationError("PaymentEvent is required.")
    if payment_event is None:
        payment_event = (
            PaymentEvent.objects.select_related("user")
            .filter(id=payment_event_id)
            .first()
        )
        if payment_event is None:
            raise ValidationError("PaymentEvent not found.")
    if payment_event.status == PaymentEventStatus.FAILED:
        raise ValidationError("PaymentEvent is failed.")
    if not payment_event.verified_at:
        raise ValidationError("PaymentEvent is unverified.")
    return mint_for_payment(payment_event=payment_event, metadata=metadata)
