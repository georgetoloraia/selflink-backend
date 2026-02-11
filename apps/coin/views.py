from __future__ import annotations

import base64
import json
from datetime import timedelta, timezone as dt_timezone

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.coin.models import (
    COIN_CURRENCY,
    SYSTEM_ACCOUNT_REVENUE,
    CoinAccount,
    CoinEvent,
    CoinEventType,
    CoinLedgerEntry,
    CoinLedgerEntryDirection,
    EntitlementKey,
    PaidProduct,
    UserEntitlement,
)
from apps.coin.serializers import (
    CoinLedgerEntrySerializer,
    CoinPurchaseSerializer,
    CoinSpendSerializer,
    CoinTransferSerializer,
    EntitlementSerializer,
    PaidProductSerializer,
    empty_entitlements_payload,
)
from apps.coin.services.ledger import (
    create_spend,
    create_transfer,
    get_balance_cents,
    get_or_create_user_account,
    post_event_and_entries,
)


class CoinBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        account = get_or_create_user_account(request.user)
        balance_cents = get_balance_cents(account.account_key)
        return Response({"account_key": account.account_key, "balance_cents": balance_cents, "currency": "SLC"})


class CoinLedgerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _decode_cursor(cursor_raw: str) -> tuple[timezone.datetime, int]:
        padding = "=" * (-len(cursor_raw) % 4)
        try:
            decoded = base64.urlsafe_b64decode(cursor_raw + padding)
            payload = json.loads(decoded.decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Invalid cursor.") from None
        if not isinstance(payload, dict):
            raise ValueError("Invalid cursor.")
        ts_raw = payload.get("ts")
        entry_id = payload.get("id")
        if not isinstance(ts_raw, str) or not isinstance(entry_id, int):
            raise ValueError("Invalid cursor.")
        dt = parse_datetime(ts_raw)
        if dt is None:
            raise ValueError("Invalid cursor.")
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, dt_timezone.utc)
        else:
            dt = dt.astimezone(dt_timezone.utc)
        return dt, entry_id

    @staticmethod
    def _encode_cursor(entry: CoinLedgerEntry) -> str:
        ts = entry.created_at.astimezone(dt_timezone.utc).isoformat()
        payload = json.dumps({"ts": ts, "id": entry.id}, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")

    def _parse_cursor(self, cursor_raw: str) -> tuple[timezone.datetime, int]:
        if cursor_raw.isdigit():
            entry = CoinLedgerEntry.objects.only("id", "created_at").filter(id=int(cursor_raw)).first()
            if entry is None:
                raise ValueError("Invalid cursor.")
            return entry.created_at, entry.id
        return self._decode_cursor(cursor_raw)

    def get(self, request: Request) -> Response:
        account = get_or_create_user_account(request.user)
        limit_raw = request.query_params.get("limit", "50")
        cursor_raw = request.query_params.get("cursor")
        try:
            limit = max(1, min(int(limit_raw), 200))
        except ValueError:
            return Response({"detail": "Invalid limit."}, status=status.HTTP_400_BAD_REQUEST)

        qs = (
            CoinLedgerEntry.objects.select_related("event")
            .filter(account_key=account.account_key)
            .order_by("created_at", "id")
        )
        if cursor_raw:
            try:
                cursor_dt, cursor_id = self._parse_cursor(cursor_raw)
            except (ValueError, TypeError):
                return Response({"detail": "Invalid cursor."}, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(Q(created_at__gt=cursor_dt) | Q(created_at=cursor_dt, id__gt=cursor_id))

        entries = list(qs[:limit])
        serializer = CoinLedgerEntrySerializer(entries, many=True)
        next_cursor = None
        if len(entries) == limit:
            last = entries[-1]
            next_cursor = self._encode_cursor(last)
        return Response({"results": serializer.data, "next_cursor": next_cursor})


class CoinTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "coin_transfer"

    @staticmethod
    def _error_payload(detail: str) -> dict:
        code_map = {
            "insufficient_funds": "insufficient_funds",
            "Cannot transfer to the same user.": "invalid_receiver",
            "Amount must be positive.": "invalid_amount",
            "Coin account is not active.": "account_inactive",
            "User coin accounts cannot be system accounts.": "account_invalid",
        }
        code = code_map.get(detail, "coin_error")
        return {"detail": detail, "code": code}

    def post(self, request: Request) -> Response:
        serializer = CoinTransferSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except DRFValidationError as exc:
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict) and ("receiver_account_key" in detail or "to_user_id" in detail):
                return Response({"detail": "invalid_receiver", "code": "invalid_receiver"}, status=400)
            if detail == "invalid_receiver":
                return Response({"detail": "invalid_receiver", "code": "invalid_receiver"}, status=400)
            raise
        receiver = serializer.validated_data["receiver_user"]
        amount_cents = int(serializer.validated_data["amount_cents"])
        fee_cents = int(serializer.validated_data["fee_cents"])
        note = serializer.validated_data.get("note", "")

        try:
            event = create_transfer(
                sender=request.user,
                receiver=receiver,
                amount_cents=amount_cents,
                fee_cents=fee_cents,
                note=note,
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response(self._error_payload(detail), status=status.HTTP_400_BAD_REQUEST)

        sender_account = get_or_create_user_account(request.user)
        sender_balance_cents = get_balance_cents(sender_account.account_key)
        return Response(
            {
                "event_id": event.id,
                "to_user_id": receiver.id,
                "amount_cents": amount_cents,
                "fee_cents": fee_cents,
                "total_debit_cents": amount_cents + fee_cents,
                "balance_cents": sender_balance_cents,
                "currency": "SLC",
            },
            status=status.HTTP_201_CREATED,
        )


class CoinSpendView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "coin_spend"

    @staticmethod
    def _error_payload(detail: str) -> dict:
        code_map = {
            "insufficient_funds": "insufficient_funds",
            "Amount must be positive.": "invalid_amount",
            "Coin account is not active.": "account_inactive",
            "User coin accounts cannot be system accounts.": "account_invalid",
        }
        code = code_map.get(detail, "coin_error")
        return {"detail": detail, "code": code}

    def post(self, request: Request) -> Response:
        serializer = CoinSpendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount_cents = int(serializer.validated_data["amount_cents"])
        reference = serializer.validated_data["reference"]
        note = serializer.validated_data.get("note", "")

        try:
            event = create_spend(
                user=request.user,
                amount_cents=amount_cents,
                reference=reference,
                note=note,
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response(self._error_payload(detail), status=status.HTTP_400_BAD_REQUEST)

        account = get_or_create_user_account(request.user)
        balance_cents = get_balance_cents(account.account_key)
        return Response(
            {
                "event_id": event.id,
                "amount_cents": amount_cents,
                "reference": reference,
                "balance_cents": balance_cents,
                "currency": "SLC",
            },
            status=status.HTTP_201_CREATED,
        )


class CoinProductsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        products = PaidProduct.objects.filter(is_active=True).order_by("sort_order", "price_slc")
        serializer = PaidProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CoinPurchaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "coin_spend"

    @staticmethod
    def _error_payload(detail: str, code: str | None = None) -> dict:
        return {"detail": detail, "code": code or detail}

    def _build_entitlements_payload(self, user) -> dict[str, dict[str, object]]:
        payload = empty_entitlements_payload()
        entitlements = UserEntitlement.objects.filter(
            user=user,
            key__in=[EntitlementKey.PREMIUM, EntitlementKey.PREMIUM_PLUS],
        )
        serializer = EntitlementSerializer(entitlements, many=True)
        for entry in serializer.data:
            key = entry.get("key")
            if key:
                payload[key] = {
                    "active": entry.get("active", False),
                    "active_until": entry.get("active_until"),
                }
        return payload

    def _apply_entitlement(
        self,
        *,
        user,
        key: str,
        duration_days: int | None,
        quantity: int,
        meta: dict,
        source: str = "slc",
    ) -> UserEntitlement:
        now = timezone.now()
        entitlement = UserEntitlement.objects.select_for_update().filter(user=user, key=key).first()
        base_time = now
        if entitlement and entitlement.active_until and entitlement.active_until > now:
            base_time = entitlement.active_until
        if duration_days is None:
            active_until = None
        else:
            active_until = base_time + timedelta(days=duration_days * quantity)
        if entitlement:
            entitlement.active_until = active_until
            entitlement.source = source
            entitlement.meta = meta
            entitlement.save(update_fields=["active_until", "source", "meta", "updated_at"])
            return entitlement
        return UserEntitlement.objects.create(
            user=user,
            key=key,
            active_until=active_until,
            source=source,
            meta=meta,
        )

    def post(self, request: Request) -> Response:
        serializer = CoinPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_code = serializer.validated_data["product_code"]
        quantity = int(serializer.validated_data.get("quantity") or 1)
        idempotency_key = serializer.validated_data["idempotency_key"].strip()

        product = PaidProduct.objects.filter(code=product_code, is_active=True).first()
        if not product:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        if quantity < 1 or quantity > 12:
            return Response(self._error_payload("invalid_quantity", "invalid_quantity"), status=400)
        if not idempotency_key:
            return Response(self._error_payload("idempotency_key_required", "idempotency_key_required"), status=400)

        total_price = int(product.price_slc) * quantity
        if total_price <= 0:
            return Response(self._error_payload("invalid_amount", "invalid_amount"), status=400)

        account = get_or_create_user_account(request.user)
        purchase_idempotency = f"purchase:{request.user.id}:{idempotency_key}"
        existing = CoinEvent.objects.filter(idempotency_key=purchase_idempotency).first()
        if existing:
            meta = existing.metadata or {}
            if meta.get("product_code") and meta.get("product_code") != product.code:
                return Response(
                    self._error_payload("idempotency_conflict", "idempotency_conflict"),
                    status=status.HTTP_409_CONFLICT,
                )
            entitlements = self._build_entitlements_payload(request.user)
            balance = get_balance_cents(account.account_key)
            charged_slc = int(meta.get("total_price_slc") or total_price)
            return Response(
                {
                    "ok": True,
                    "product_code": product.code,
                    "charged_slc": charged_slc,
                    "balance_slc": balance,
                    "entitlements": entitlements,
                    "ledger_tx_id": str(existing.id),
                },
                status=status.HTTP_200_OK,
            )

        try:
            with transaction.atomic():
                CoinAccount.objects.select_for_update().filter(id=account.id).get()
                balance = get_balance_cents(account.account_key)
                if balance < total_price:
                    return Response(self._error_payload("insufficient_funds", "insufficient_funds"), status=402)

                event_meta = {
                    "user_id": request.user.id,
                    "product_code": product.code,
                    "entitlement_key": product.entitlement_key,
                    "quantity": quantity,
                    "unit_price_slc": int(product.price_slc),
                    "total_price_slc": total_price,
                    "reference": f"product:{product.code}",
                }
                try:
                    event = post_event_and_entries(
                        event_type=CoinEventType.SPEND,
                        created_by=request.user,
                        idempotency_key=purchase_idempotency,
                        metadata=event_meta,
                        entries=[
                            {
                                "account_key": account.account_key,
                                "amount_cents": total_price,
                                "currency": COIN_CURRENCY,
                                "direction": CoinLedgerEntryDirection.DEBIT,
                            },
                            {
                                "account_key": SYSTEM_ACCOUNT_REVENUE,
                                "amount_cents": total_price,
                                "currency": COIN_CURRENCY,
                                "direction": CoinLedgerEntryDirection.CREDIT,
                            },
                        ],
                    )
                except IntegrityError:
                    event = CoinEvent.objects.filter(idempotency_key=purchase_idempotency).first()
                    if not event:
                        raise

                meta = {
                    "product_code": product.code,
                    "quantity": quantity,
                    "unit_price_slc": int(product.price_slc),
                    "total_price_slc": total_price,
                }
                entitlement = self._apply_entitlement(
                    user=request.user,
                    key=product.entitlement_key,
                    duration_days=product.duration_days,
                    quantity=quantity,
                    meta=meta,
                )
                if product.entitlement_key == EntitlementKey.PREMIUM_PLUS:
                    premium = self._apply_entitlement(
                        user=request.user,
                        key=EntitlementKey.PREMIUM,
                        duration_days=product.duration_days,
                        quantity=quantity,
                        meta={"source": "premium_plus"},
                    )
                    if entitlement.active_until and premium.active_until and premium.active_until < entitlement.active_until:
                        premium.active_until = entitlement.active_until
                        premium.save(update_fields=["active_until", "updated_at"])
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response(self._error_payload(detail), status=status.HTTP_400_BAD_REQUEST)

        entitlements = self._build_entitlements_payload(request.user)
        balance = get_balance_cents(account.account_key)
        return Response(
            {
                "ok": True,
                "product_code": product.code,
                "charged_slc": total_price,
                "balance_slc": balance,
                "entitlements": entitlements,
                "ledger_tx_id": str(event.id) if event else None,
            },
            status=status.HTTP_200_OK,
        )


class MeEntitlementsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        entitlements = UserEntitlement.objects.filter(
            user=request.user,
            key__in=[EntitlementKey.PREMIUM, EntitlementKey.PREMIUM_PLUS],
        )
        serializer = EntitlementSerializer(entitlements, many=True)
        payload = empty_entitlements_payload()
        for entry in serializer.data:
            key = entry.get("key")
            if key:
                payload[key] = {
                    "active": entry.get("active", False),
                    "active_until": entry.get("active_until"),
                }
        return Response(payload, status=status.HTTP_200_OK)
