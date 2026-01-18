from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest


@dataclass(frozen=True)
class BtcPayWebhookEvent:
    invoice_id: str
    event_type: str


@dataclass(frozen=True)
class BtcPayInvoice:
    invoice_id: str
    amount_cents: int
    currency: str
    status: str
    reference: str


@dataclass(frozen=True)
class BtcPayCheckoutResult:
    invoice_id: str
    checkout_url: str


def _normalize_currency(currency: str) -> str:
    return str(currency or "").strip().upper()


def _normalize_status(status: str) -> str:
    return str(status or "").strip().lower()


def _parse_amount_cents(raw_amount) -> int:
    if raw_amount in (None, ""):
        raise ValidationError("Payment amount is required.")

    amount_in_cents = bool(getattr(settings, "BTCPAY_AMOUNT_IN_CENTS", False))
    if isinstance(raw_amount, int):
        amount_cents = raw_amount if amount_in_cents else raw_amount * 100
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


def parse_webhook_event(body: bytes) -> BtcPayWebhookEvent:
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid JSON payload.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Invalid payload format.")

    invoice_id = payload.get("invoiceId") or payload.get("invoice_id") or payload.get("id")
    invoice_id = str(invoice_id or "").strip()
    if not invoice_id:
        raise ValidationError("invoice_id is required.")

    event_type = payload.get("type") or payload.get("eventType") or payload.get("event_type")
    event_type = str(event_type or "").strip()
    if not event_type:
        raise ValidationError("event_type is required.")

    return BtcPayWebhookEvent(invoice_id=invoice_id, event_type=event_type)


def normalize_invoice(payload: dict) -> BtcPayInvoice:
    if not isinstance(payload, dict):
        raise ValidationError("Invalid invoice payload.")

    invoice_id = payload.get("id") or payload.get("invoiceId") or payload.get("invoice_id")
    invoice_id = str(invoice_id or "").strip()
    if not invoice_id:
        raise ValidationError("invoice_id is required.")

    raw_amount = payload.get("amount")
    if raw_amount is None:
        raw_amount = payload.get("price")
    if raw_amount is None:
        raw_amount = payload.get("amount_cents")
    amount_cents = _parse_amount_cents(raw_amount)

    currency = _normalize_currency(payload.get("currency") or payload.get("currencyCode"))
    if not currency:
        raise ValidationError("currency is required.")

    allowed = [code.upper() for code in (getattr(settings, "BTCPAY_ALLOWED_CURRENCIES", []) or [])]
    if allowed and currency not in allowed:
        raise ValidationError("currency is not allowed.")

    status = _normalize_status(payload.get("status") or payload.get("state"))
    if not status:
        raise ValidationError("status is required.")

    metadata = payload.get("metadata") or {}
    reference = ""
    if isinstance(metadata, dict):
        reference = str(metadata.get("reference") or metadata.get("orderId") or metadata.get("order_id") or "")

    return BtcPayInvoice(
        invoice_id=invoice_id,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        reference=reference,
    )


def verify_webhook_signature(request: HttpRequest) -> None:
    secret = str(getattr(settings, "BTCPAY_WEBHOOK_SECRET", "") or "")
    if not secret:
        raise ValidationError("BTCPAY_WEBHOOK_SECRET is not configured.")
    header_name = str(getattr(settings, "BTCPAY_SIGNATURE_HEADER", "HTTP_BTCPAY_SIG") or "")
    signature = request.META.get(header_name, "")
    if not signature:
        raise ValidationError("Missing BTCPay signature.")

    expected = hmac.new(secret.encode("utf-8"), request.body, hashlib.sha256).hexdigest()
    candidate = signature
    if "=" in candidate:
        _, candidate = candidate.split("=", 1)
    if not hmac.compare_digest(candidate, expected):
        raise ValidationError("Invalid BTCPay signature.")


class BtcPayClient:
    def __init__(self, *, base_url: str, api_key: str, store_id: str, timeout: int = 10) -> None:
        self.base_url = str(base_url or "").rstrip("/")
        self.api_key = str(api_key or "").strip()
        self.store_id = str(store_id or "").strip()
        self.timeout = int(timeout or 10)
        if not self.base_url:
            raise ValidationError("BTCPAY_BASE_URL is required.")
        if not self.api_key:
            raise ValidationError("BTCPAY_API_KEY is required.")
        if not self.store_id:
            raise ValidationError("BTCPAY_STORE_ID is required.")

    def _request_json(self, *, method: str, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"token {self.api_key}")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8") or "{}"
        except urllib.error.HTTPError as exc:
            raise ValidationError(f"BTCPay API error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ValidationError("BTCPay API unavailable.") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValidationError("BTCPay API returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValidationError("BTCPay API returned invalid response.")
        return payload

    def create_invoice(self, *, amount_cents: int, currency: str, reference: str) -> BtcPayCheckoutResult:
        amount_major = (Decimal(amount_cents) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        payload = {
            "amount": str(amount_major),
            "currency": currency,
            "metadata": {"reference": reference},
        }
        data = self._request_json(
            method="POST",
            path=f"/api/v1/stores/{self.store_id}/invoices",
            payload=payload,
        )
        invoice_id = str(data.get("id") or "").strip()
        checkout_url = str(data.get("checkoutLink") or data.get("checkout_url") or "").strip()
        if not invoice_id:
            raise ValidationError("BTCPay invoice id is missing.")
        if not checkout_url:
            raise ValidationError("BTCPay checkout link is missing.")
        return BtcPayCheckoutResult(invoice_id=invoice_id, checkout_url=checkout_url)

    def get_invoice(self, *, invoice_id: str) -> dict:
        if not invoice_id:
            raise ValidationError("invoice_id is required.")
        return self._request_json(
            method="GET",
            path=f"/api/v1/stores/{self.store_id}/invoices/{invoice_id}",
            payload=None,
        )


def get_btcpay_client() -> BtcPayClient:
    return BtcPayClient(
        base_url=getattr(settings, "BTCPAY_BASE_URL", ""),
        api_key=getattr(settings, "BTCPAY_API_KEY", ""),
        store_id=getattr(settings, "BTCPAY_STORE_ID", ""),
        timeout=int(getattr(settings, "BTCPAY_TIMEOUT_SECONDS", 10)),
    )
