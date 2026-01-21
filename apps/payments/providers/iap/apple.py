from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError

from . import VerificationResult


def verify_apple_receipt(
    *,
    receipt: str,
    expected_product_id: str,
    expected_transaction_id: str,
) -> VerificationResult:
    if not receipt:
        raise ValidationError("receipt is required.")
    if not expected_product_id or not expected_transaction_id:
        raise ValidationError("product_id and transaction_id are required.")

    if not settings.APPLE_IAP_BUNDLE_ID or not settings.APPLE_IAP_SHARED_SECRET:
        raise ValidationError("Apple IAP verification not configured.")

    raise ValidationError("Apple IAP verification not implemented.")
