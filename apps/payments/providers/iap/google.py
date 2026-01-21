from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError

from . import VerificationResult


def verify_google_purchase(
    *,
    purchase_token: str,
    expected_product_id: str,
    expected_order_id: str,
) -> VerificationResult:
    if not purchase_token:
        raise ValidationError("purchase_token is required.")
    if not expected_product_id or not expected_order_id:
        raise ValidationError("product_id and order_id are required.")

    if not settings.GOOGLE_IAP_PACKAGE_NAME or not settings.GOOGLE_IAP_SERVICE_ACCOUNT_JSON:
        raise ValidationError("Google IAP verification not configured.")

    raise ValidationError("Google IAP verification not implemented.")
