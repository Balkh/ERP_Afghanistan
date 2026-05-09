from django.urls import path, include
from rest_framework.routers import DefaultRouter
from cost_centers.views import CostCenterViewSet, CostAllocationViewSet, CostTransactionViewSet

router = DefaultRouter()
router.register(r'centers', CostCenterViewSet, basename='costcenter')
router.register(r'allocations', CostAllocationViewSet, basename='costallocation')
router.register(r'transactions', CostTransactionViewSet, basename='costtransaction')

urlpatterns = [
    path('', include(router.urls)),
]