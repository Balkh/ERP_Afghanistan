from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounting import views
from accounting.views_account import (
    AccountViewSet, JournalEntryViewSet, JournalEventLogViewSet,
    export_report, advanced_report, report_options
)

# Router for account views
router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'journal-entries', JournalEntryViewSet, basename='journalentry')
router.register(r'journal-events', JournalEventLogViewSet, basename='journalevent')

urlpatterns = [
    # Calculation endpoints
    path('calculate-invoice/', views.calculate_invoice, name='calculate_invoice'),
    path('convert-currency/', views.convert_currency, name='convert_currency'),
    path('currencies/', views.get_currencies, name='get_currencies'),
    path('exchange-rates/', views.get_exchange_rates, name='get_exchange_rates'),
    path('calculate-mixed-payment/', views.calculate_mixed_payment, name='calculate_mixed_payment'),
    path('calculate-discount/', views.calculate_discount, name='calculate_discount'),
    path('calculate-tax/', views.calculate_tax, name='calculate_tax'),
    # Export endpoint
    path('export/', export_report, name='export_report'),
    # Advanced reports endpoints
    path('reports/', advanced_report, name='advanced_report'),
    path('report-options/', report_options, name='report_options'),
    # Account and journal entry endpoints
    path('', include(router.urls)),
]
