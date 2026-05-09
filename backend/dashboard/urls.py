from rest_framework.routers import DefaultRouter
from dashboard.views import (
    DashboardWidgetConfigViewSet,
    DashboardAlertViewSet,
    DashboardKPIController,
    DashboardWidgetController,
    DrillDownController
)

router = DefaultRouter()
router.register(r'widget-configs', DashboardWidgetConfigViewSet, basename='widget-config')
router.register(r'alerts', DashboardAlertViewSet, basename='dashboard-alert')
router.register(r'kpis', DashboardKPIController, basename='dashboard-kpi')
router.register(r'widgets', DashboardWidgetController, basename='dashboard-widget')
router.register(r'drilldown', DrillDownController, basename='drill-down')

urlpatterns = router.urls