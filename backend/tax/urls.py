from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tax.views import (
    TaxCategoryViewSet, TaxRateViewSet, TaxJurisdictionViewSet,
    TaxReturnViewSet, TaxTransactionViewSet
)

router = DefaultRouter()
router.register(r'categories', TaxCategoryViewSet, basename='taxcategory')
router.register(r'rates', TaxRateViewSet, basename='taxrate')
router.register(r'jurisdictions', TaxJurisdictionViewSet, basename='taxjurisdiction')
router.register(r'returns', TaxReturnViewSet, basename='taxreturn')
router.register(r'transactions', TaxTransactionViewSet, basename='taxtxn')

urlpatterns = [
    path('', include(router.urls)),
]