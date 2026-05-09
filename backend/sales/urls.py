from django.urls import path, include
from rest_framework.routers import DefaultRouter
from sales.views import (
    CustomerViewSet,
    SalesInvoiceViewSet,
    SalesItemViewSet,
    CustomerPaymentViewSet,
)

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'invoices', SalesInvoiceViewSet, basename='salesinvoice')
router.register(r'items', SalesItemViewSet, basename='salesitem')
router.register(r'payments', CustomerPaymentViewSet, basename='customerpayment')

urlpatterns = [
    path('', include(router.urls)),
]
