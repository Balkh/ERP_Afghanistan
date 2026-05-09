from rest_framework.routers import DefaultRouter
from entities.views import EntityViewSet, EntityAccountViewSet, InterCompanyTransactionViewSet

router = DefaultRouter()
router.register(r'entities', EntityViewSet, basename='entity')
router.register(r'entity-accounts', EntityAccountViewSet, basename='entity-account')
router.register(r'inter-company', InterCompanyTransactionViewSet, basename='inter-company')

urlpatterns = router.urls