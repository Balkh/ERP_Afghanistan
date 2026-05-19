"""Insurance API Routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'providers', views.InsuranceProviderViewSet)
router.register(r'policies', views.InsurancePolicyViewSet)
router.register(r'claims', views.ClaimViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
