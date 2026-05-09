from rest_framework.routers import DefaultRouter
from cashflow.views import (
    CashFlowForecastViewSet, CashFlowItemViewSet, CashFlowScenarioViewSet
)

router = DefaultRouter()
router.register(r'forecasts', CashFlowForecastViewSet, basename='cashflow-forecast')
router.register(r'items', CashFlowItemViewSet, basename='cashflow-item')
router.register(r'scenarios', CashFlowScenarioViewSet, basename='cashflow-scenario')

urlpatterns = router.urls