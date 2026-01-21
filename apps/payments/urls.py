from django.urls import path
from rest_framework.routers import DefaultRouter

from .btcpay import BtcPayCheckoutView
from .iap import IapVerifyView
from .ipay import IpayCheckoutView
from .stripe_checkout import StripeCheckoutView
from .views import GiftTypeViewSet, PlanViewSet, SubscriptionViewSet
from .webhook import StripeWebhookView
from .webhooks.btcpay_webhook import BtcPayWebhookView
from .webhooks.ipay_webhook import IpayWebhookView

router = DefaultRouter()
router.register(r"payments/plans", PlanViewSet, basename="payment-plan")
router.register(r"payments/gifts", GiftTypeViewSet, basename="gift-type")
router.register(r"payments/subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = router.urls + [
    path("payments/stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("payments/stripe/checkout/", StripeCheckoutView.as_view(), name="stripe-checkout"),
    path("payments/ipay/webhook/", IpayWebhookView.as_view(), name="ipay-webhook"),
    path("payments/ipay/checkout/", IpayCheckoutView.as_view(), name="ipay-checkout"),
    path("payments/iap/verify/", IapVerifyView.as_view(), name="iap-verify"),
    path("payments/btcpay/webhook/", BtcPayWebhookView.as_view(), name="btcpay-webhook"),
    path("payments/btcpay/checkout/", BtcPayCheckoutView.as_view(), name="btcpay-checkout"),
]
