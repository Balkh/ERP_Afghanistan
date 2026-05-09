from rest_framework.routers import DefaultRouter
from audit.views import AuditTrailViewSet, AuditRetentionPolicyViewSet

router = DefaultRouter()
router.register(r'logs', AuditTrailViewSet, basename='audit-trail')
router.register(r'policies', AuditRetentionPolicyViewSet, basename='audit-policy')

urlpatterns = router.urls