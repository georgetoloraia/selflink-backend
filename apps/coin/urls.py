from django.urls import path

from apps.coin.views import (
    CoinBalanceView,
    CoinLedgerView,
    CoinProductsView,
    CoinPurchaseView,
    CoinSpendView,
    CoinTransferView,
    MeEntitlementsView,
)

app_name = "coin"

urlpatterns = [
    path("coin/balance/", CoinBalanceView.as_view(), name="coin-balance"),
    path("coin/ledger/", CoinLedgerView.as_view(), name="coin-ledger"),
    path("coin/transfer/", CoinTransferView.as_view(), name="coin-transfer"),
    path("coin/spend/", CoinSpendView.as_view(), name="coin-spend"),
    path("coin/products/", CoinProductsView.as_view(), name="coin-products"),
    path("coin/purchase/", CoinPurchaseView.as_view(), name="coin-purchase"),
    path("me/entitlements/", MeEntitlementsView.as_view(), name="me-entitlements"),
]
