from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest


@dataclass(frozen=True)
class IpayEvent:
    provider_event_id: str
    reference: str
    status: str
    amount_cents: int
    currency: str
    event_type: str


def _normalize_status(status: str) -> str:
    return str(status or "").strip().lower()


def _normalize_currency(currency: str) -> str:
    return str(currency or "").strip().upper()


def _get_setting_value(name: str) -> str:
    return str(getattr(settings, name, "") or "").strip()


def _extract_value(payload: dict, keys: list[str], override_key: str | None = None) -> str:
    if override_key:
        value = payload.get(override_key)
        if value not in (None, ""):
            return str(value)
        return ""
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return str(payload[key])
    return ""


def _parse_amount_cents(raw_amount, currency: str) -> int:
    if isinstance(raw_amount, dict):
        if "currency" in raw_amount and not currency:
            currency = str(raw_amount.get("currency") or "")
        raw_amount = (
            raw_amount.get("amount")
            if raw_amount.get("amount") is not None
            else raw_amount.get("value")
            if raw_amount.get("value") is not None
            else raw_amount.get("total")
        )

    if raw_amount in (None, ""):
        raise ValidationError("Payment amount is required.")

    amount_in_cents = bool(getattr(settings, "IPAY_AMOUNT_IN_CENTS", True))
    if isinstance(raw_amount, int):
        amount_cents = raw_amount if amount_in_cents else int(Decimal(raw_amount) * 100)
    else:
        raw_text = str(raw_amount)
        try:
            value = Decimal(raw_text)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("Payment amount is invalid.") from exc
        looks_like_major = "." in raw_text or "," in raw_text
        if amount_in_cents and value == value.to_integral_value() and not looks_like_major:
            amount_cents = int(value)
        else:
            amount_cents = int((value * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    if amount_cents <= 0:
        raise ValidationError("Payment amount must be positive.")
    return amount_cents


def parse_event(body: bytes) -> IpayEvent:
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid JSON payload.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Invalid payload format.")

    event_id_override = _get_setting_value("IPAY_FIELD_EVENT_ID")
    reference_override = _get_setting_value("IPAY_FIELD_REFERENCE")
    status_override = _get_setting_value("IPAY_FIELD_STATUS")
    amount_override = _get_setting_value("IPAY_FIELD_AMOUNT")
    currency_override = _get_setting_value("IPAY_FIELD_CURRENCY")

    event_id = _extract_value(payload, ["event_id", "payment_id", "transaction_id", "id"], event_id_override)
    reference = _extract_value(payload, ["order_id", "reference", "merchant_order_id", "external_id"], reference_override)
    if not event_id and reference:
        event_id = reference
    if not event_id:
        raise ValidationError("provider_event_id is required.")
    if not reference:
        raise ValidationError("payment reference is required.")

    status_raw = _extract_value(payload, ["status", "payment_status", "state"], status_override)
    status = _normalize_status(status_raw)
    if not status:
        raise ValidationError("payment status is required.")

    currency_raw = _extract_value(payload, ["currency", "currency_code"], currency_override)
    raw_amount = payload.get(amount_override) if amount_override else None
    if raw_amount is None:
        raw_amount = payload.get("amount_cents")
    if raw_amount is None:
        raw_amount = payload.get("amount")
    if raw_amount is None:
        raw_amount = payload.get("total_amount")
    amount_cents = _parse_amount_cents(raw_amount, currency_raw)

    currency = _normalize_currency(currency_raw)
    if not currency and isinstance(raw_amount, dict):
        currency = _normalize_currency(str(raw_amount.get("currency") or ""))
    if not currency:
        raise ValidationError("currency is required.")

    allowed = [code.upper() for code in getattr(settings, "IPAY_ALLOWED_CURRENCIES", []) or []]
    if allowed and currency not in allowed:
        raise ValidationError("currency is not allowed.")

    event_type = _extract_value(payload, ["event_type", "type", "event"], None) or "ipay.payment"

    return IpayEvent(
        provider_event_id=event_id,
        reference=reference,
        status=status,
        amount_cents=amount_cents,
        currency=currency,
        event_type=event_type,
    )


def verify_webhook_signature(request: HttpRequest) -> None:
    secret = str(getattr(settings, "IPAY_WEBHOOK_SECRET", "") or "")
    if not secret:
        raise ValidationError("IPAY_WEBHOOK_SECRET is not configured.")
    header_name = str(getattr(settings, "IPAY_SIGNATURE_HEADER", "HTTP_X_IPAY_SIGNATURE") or "")
    signature = request.META.get(header_name, "")
    if not signature:
        raise ValidationError("Missing iPay signature.")

    digest = hmac.new(secret.encode("utf-8"), request.body, hashlib.sha256).digest()
    expected_hex = hmac.new(secret.encode("utf-8"), request.body, hashlib.sha256).hexdigest()
    expected_b64 = base64.b64encode(digest).decode("ascii")

    candidate = signature
    if "=" in candidate:
        _, candidate = candidate.split("=", 1)

    if not (
        hmac.compare_digest(candidate, expected_hex)
        or hmac.compare_digest(candidate, expected_b64)
    ):
        raise ValidationError("Invalid iPay signature.")
