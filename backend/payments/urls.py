from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments.views import (
    PaymentMethodViewSet,
    PaymentAccountViewSet,
    FinancialTransactionViewSet,
    SettlementViewSet,
    PaymentDashboardViewSet,
)

router = DefaultRouter()
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'accounts', PaymentAccountViewSet, basename='payment-account')
router.register(r'transactions', FinancialTransactionViewSet, basename='financial-transaction')
router.register(r'settlements', SettlementViewSet, basename='settlement')
router.register(r'dashboard', PaymentDashboardViewSet, basename='payment-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
