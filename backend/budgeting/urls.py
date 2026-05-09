from django.urls import path, include
from rest_framework.routers import DefaultRouter
from budgeting.views import BudgetViewSet, BudgetLineViewSet

router = DefaultRouter()
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'lines', BudgetLineViewSet, basename='budgetline')

urlpatterns = [
    path('', include(router.urls)),
]