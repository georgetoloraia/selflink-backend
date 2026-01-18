from django.urls import path
from rest_framework.routers import DefaultRouter

from .ipay import IpayCheckoutView
from .views import GiftTypeViewSet, PlanViewSet, SubscriptionViewSet
from .webhook import StripeWebhookView
from .webhooks.ipay_webhook import IpayWebhookView

router = DefaultRouter()
router.register(r"payments/plans", PlanViewSet, basename="payment-plan")
router.register(r"payments/gifts", GiftTypeViewSet, basename="gift-type")
router.register(r"payments/subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = router.urls + [
    path("payments/stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("payments/ipay/webhook/", IpayWebhookView.as_view(), name="ipay-webhook"),
    path("payments/ipay/checkout/", IpayCheckoutView.as_view(), name="ipay-checkout"),
]
