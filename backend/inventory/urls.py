from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, UnitViewSet, ProductViewSet, BatchViewSet, WarehouseViewSet, StockMovementViewSet
from .views_integration import (
    allocate_stock,
    process_sale_stock,
    process_purchase_stock,
    check_stock_availability,
    get_stock_levels,
    get_available_batches,
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'units', UnitViewSet)
router.register(r'products', ProductViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'stock-movements', StockMovementViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    # Stock integration endpoints
    path('stock/allocate/', allocate_stock, name='allocate_stock'),
    path('stock/process-sale/', process_sale_stock, name='process_sale_stock'),
    path('stock/process-purchase/', process_purchase_stock, name='process_purchase_stock'),
    path('stock/check-availability/', check_stock_availability, name='check_stock_availability'),
    path('stock/levels/', get_stock_levels, name='get_stock_levels'),
    path('stock/products/<uuid:product_id>/available-batches/', get_available_batches, name='get_available_batches'),
]
