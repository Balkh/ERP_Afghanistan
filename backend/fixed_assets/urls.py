from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fixed_assets.views import (
    AssetCategoryViewSet,
    FixedAssetViewSet,
    AssetDepreciationViewSet,
    AssetDisposalViewSet,
)

router = DefaultRouter()
router.register(r'categories', AssetCategoryViewSet, basename='assetcategory')
router.register(r'assets', FixedAssetViewSet, basename='fixedasset')
router.register(r'depreciations', AssetDepreciationViewSet, basename='assetdepreciation')
router.register(r'disposals', AssetDisposalViewSet, basename='assetdisposal')

urlpatterns = [
    path('', include(router.urls)),
]