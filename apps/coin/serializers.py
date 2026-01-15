from __future__ import annotations

from rest_framework import serializers

from apps.coin.models import CoinLedgerEntry
from apps.coin.services.ledger import calculate_fee_cents
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
    to_user_id = serializers.IntegerField(min_value=1)
    amount_cents = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs: dict) -> dict:
        receiver_id = attrs.get("to_user_id")
        receiver = User.objects.filter(id=receiver_id).first()
        if receiver is None:
            raise serializers.ValidationError({"to_user_id": "Receiver not found."})
        request = self.context.get("request")
        if request and getattr(request, "user", None) == receiver:
            raise serializers.ValidationError({"to_user_id": "Cannot transfer to yourself."})
        amount_cents = int(attrs.get("amount_cents") or 0)
        fee_cents = calculate_fee_cents(amount_cents)
        if amount_cents <= fee_cents:
            raise serializers.ValidationError({"amount_cents": "Amount must be greater than the transfer fee."})
        attrs["receiver_user"] = receiver
        attrs["fee_cents"] = fee_cents
        return attrs


class CoinSpendSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=128)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
