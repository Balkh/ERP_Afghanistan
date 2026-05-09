from django.urls import path, include
from rest_framework.routers import DefaultRouter
from purchases.views import (
    SupplierViewSet,
    PurchaseInvoiceViewSet,
    PurchaseItemViewSet,
    SupplierPaymentViewSet,
)

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'invoices', PurchaseInvoiceViewSet, basename='purchaseinvoice')
router.register(r'items', PurchaseItemViewSet, basename='purchaseitem')
router.register(r'payments', SupplierPaymentViewSet, basename='supplierpayment')

urlpatterns = [
    path('', include(router.urls)),
]
