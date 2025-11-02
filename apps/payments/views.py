from __future__ import annotations

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import GiftType, Plan, Subscription, Wallet
from .serializers import (
    GiftTypeSerializer,
    PlanSerializer,
    SubscriptionCreateSerializer,
    SubscriptionSerializer,
    WalletSerializer,
)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]


class GiftTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GiftType.objects.all()
    serializer_class = GiftTypeSerializer
    permission_classes = [permissions.AllowAny]


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        return Subscription.objects.filter(user=self.request.user).select_related("plan")

    def get_serializer_class(self):  # type: ignore[override]
        if self.action == "create":
            return SubscriptionCreateSerializer
        return super().get_serializer_class()

    def create(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()
        output = SubscriptionSerializer(subscription)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="wallet")
    def wallet(self, request: Request) -> Response:
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response(WalletSerializer(wallet).data)
