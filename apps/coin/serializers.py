from __future__ import annotations

from rest_framework import serializers

from apps.coin.models import CoinLedgerEntry
from apps.coin.services.ledger import calculate_fee_cents
from apps.coin.models import CoinAccount
from apps.users.models import User


class CoinLedgerEntrySerializer(serializers.ModelSerializer):
    event_type = serializers.CharField(source="event.event_type", read_only=True)
    occurred_at = serializers.DateTimeField(source="event.occurred_at", read_only=True)
    note = serializers.CharField(source="event.note", read_only=True)
    event_metadata = serializers.JSONField(source="event.metadata", read_only=True)

    class Meta:
        model = CoinLedgerEntry
        fields = (
            "id",
            "event_id",
            "event_type",
            "occurred_at",
            "account_key",
            "amount_cents",
            "currency",
            "direction",
            "note",
            "event_metadata",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class CoinTransferSerializer(serializers.Serializer):
    to_user_id = serializers.IntegerField(min_value=1, required=False)
    receiver_account_key = serializers.CharField(required=False, allow_blank=False)
    amount_cents = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs: dict) -> dict:
        receiver_id = attrs.get("to_user_id")
        receiver_account_key = attrs.get("receiver_account_key")
        if not receiver_id and not receiver_account_key:
            raise serializers.ValidationError("invalid_receiver")

        receiver = None
        if receiver_account_key:
            account = (
                CoinAccount.objects.filter(account_key=receiver_account_key)
                .select_related("user")
                .first()
            )
            if account is None or account.user is None:
                raise serializers.ValidationError({"receiver_account_key": "Receiver not found."})
            if account.status != CoinAccount.Status.ACTIVE:
                raise serializers.ValidationError({"receiver_account_key": "Receiver not found."})
            receiver = account.user

        if receiver_id:
            receiver = User.objects.filter(id=receiver_id).first()
            if receiver is None:
                raise serializers.ValidationError({"to_user_id": "Receiver not found."})

        if receiver_id and receiver_account_key and receiver is None:
            raise serializers.ValidationError("invalid_receiver")
        if receiver_id and receiver_account_key:
            expected_key = CoinAccount.user_account_key(receiver.id)
            if receiver_account_key != expected_key:
                raise serializers.ValidationError({"receiver_account_key": "Receiver not found."})

        request = self.context.get("request")
        if request and getattr(request, "user", None) == receiver:
            raise serializers.ValidationError({"to_user_id": "Cannot transfer to yourself."})
        amount_cents = int(attrs.get("amount_cents") or 0)
        fee_cents = 0
        attrs["receiver_user"] = receiver
        attrs["fee_cents"] = fee_cents
        return attrs


class CoinSpendSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=128)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
