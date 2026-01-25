from __future__ import annotations

import base64
import json
from datetime import timezone as dt_timezone

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.coin.models import CoinLedgerEntry
from apps.coin.serializers import CoinLedgerEntrySerializer, CoinSpendSerializer, CoinTransferSerializer
from apps.coin.services.ledger import create_spend, create_transfer, get_balance_cents, get_or_create_user_account


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
