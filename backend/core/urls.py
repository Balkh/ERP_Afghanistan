from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views_template import InvoiceTemplateViewSet

router = DefaultRouter()
router.register(r'invoice-templates', InvoiceTemplateViewSet, basename='invoice-template')

urlpatterns = [
    path('', include(router.urls)),
]
