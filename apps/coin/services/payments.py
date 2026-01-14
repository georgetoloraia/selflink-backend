from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.coin.services.ledger import mint_for_payment
from apps.users.models import User


def mint_from_payment_event(
    *,
    user: User,
    amount_cents: int,
    provider: str,
    provider_event_id: str,
    metadata: dict | None = None,
):
    if not provider_event_id:
        raise ValidationError("provider_event_id is required")
    return mint_for_payment(
        user=user,
        amount_cents=amount_cents,
        provider=provider,
        external_id=provider_event_id,
        metadata=metadata,
    )
