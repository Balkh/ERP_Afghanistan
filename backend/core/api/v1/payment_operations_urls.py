"""Phase 20: Payment Operations API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.api.v1.payment_operations import PaymentOperationsViewSet

router = DefaultRouter()
router.register(
    r'',
    PaymentOperationsViewSet,
    basename='payment-operations',
)

urlpatterns = [
    path('', include(router.urls)),
]
