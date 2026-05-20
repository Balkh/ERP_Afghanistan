from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views_template import InvoiceTemplateViewSet
from core import import_views

router = DefaultRouter()
router.register(r'invoice-templates', InvoiceTemplateViewSet, basename='invoice-template')

urlpatterns = [
    path('', include(router.urls)),
    path('import/<str:entity_type>/dry-run/', import_views.import_dry_run, name='import_dry_run'),
    path('import/<str:entity_type>/execute/', import_views.import_execute, name='import_execute'),
]
