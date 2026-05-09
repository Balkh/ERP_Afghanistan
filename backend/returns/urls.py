"""Returns API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReturnOrderViewSet, ReconciliationEntryViewSet

router = DefaultRouter()
router.register(r'return-orders', ReturnOrderViewSet, basename='returnorder')
router.register(r'reconciliation', ReconciliationEntryViewSet, basename='reconciliation')

urlpatterns = [
    path('', include(router.urls)),
]