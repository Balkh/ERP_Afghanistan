from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from accounting.models import Account, Currency
from cashflow.models import CashFlowForecast, CashFlowItem, CashFlowScenario
from cashflow.services.forecasting_service import CashFlowForecastingService

User = get_user_model()


class CashFlowForecastTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.forecast = CashFlowForecast.objects.create(
            name='Monthly Forecast',
            forecast_type='MONTHLY',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            currency=cls.currency
        )

    def test_create_forecast(self):
        self.assertEqual(self.forecast.name, 'Monthly Forecast')
        self.assertEqual(self.forecast.forecast_type, 'MONTHLY')
        self.assertTrue(self.forecast.is_active)

    def test_forecast_str(self):
        self.assertIn('Monthly Forecast', str(self.forecast))


class CashFlowItemTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.forecast = CashFlowForecast.objects.create(
            name='Test Forecast',
            forecast_type='DAILY',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            currency=cls.currency
        )

    def test_create_item(self):
        item = CashFlowItem.objects.create(
            forecast=self.forecast,
            category='SALES_RECEIPT',
            item_type='INFLOW',
            description='Test receipt',
            expected_date=date(2024, 1, 15),
            amount=Decimal('1000.00')
        )
        self.assertEqual(item.category, 'SALES_RECEIPT')
        self.assertEqual(item.item_type, 'INFLOW')

    def test_weighted_amount(self):
        item = CashFlowItem.objects.create(
            forecast=self.forecast,
            category='SALES_RECEIPT',
            item_type='INFLOW',
            description='Test receipt',
            expected_date=date(2024, 1, 15),
            amount=Decimal('1000.00'),
            probability=Decimal('80.00')
        )
        self.assertEqual(item.weighted_amount, Decimal('800.00'))


class CashFlowScenarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.scenario = CashFlowScenario.objects.create(
            name='Optimistic Scenario',
            scenario_type='OPTIMISTIC',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            currency=cls.currency,
            sales_growth_rate=Decimal('10.00')
        )

    def test_create_scenario(self):
        self.assertEqual(self.scenario.scenario_type, 'OPTIMISTIC')
        self.assertEqual(self.scenario.sales_growth_rate, Decimal('10.00'))


class CashFlowServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.account = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET',
            account_category='CURRENT_ASSET', is_active=True
        )

    def test_generate_forecast(self):
        result = CashFlowForecastingService.generate_forecast(
            date(2024, 6, 1),
            date(2024, 6, 30),
            'DAILY'
        )
        self.assertIn('items_count', result)
        self.assertIn('start_date', result)

    def test_forecast_summary(self):
        forecast = CashFlowForecast.objects.create(
            name='Summary Test',
            forecast_type='MONTHLY',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            currency=self.currency
        )
        CashFlowItem.objects.create(
            forecast=forecast,
            category='SALES_RECEIPT',
            item_type='INFLOW',
            description='Test',
            expected_date=date(2024, 6, 15),
            amount=Decimal('5000.00')
        )
        CashFlowItem.objects.create(
            forecast=forecast,
            category='PAYROLL',
            item_type='OUTFLOW',
            description='Test',
            expected_date=date(2024, 6, 15),
            amount=Decimal('3000.00')
        )
        
        summary = CashFlowForecastingService.get_forecast_summary(forecast)
        self.assertEqual(summary['total_inflow'], Decimal('5000.00'))
        self.assertEqual(summary['total_outflow'], Decimal('3000.00'))
        self.assertEqual(summary['net_position'], Decimal('2000.00'))

    def test_scenario_analysis(self):
        scenario = CashFlowScenario.objects.create(
            name='Test Scenario',
            scenario_type='REALISTIC',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            currency=self.currency
        )
        result = CashFlowForecastingService.run_scenario_analysis(scenario)
        self.assertIn('net_position', result)
        self.assertIn('daily_inflow', result)

    def test_historical_cash_flow(self):
        result = CashFlowForecastingService.get_historical_cash_flow(
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        self.assertIsInstance(result, list)

    def test_receivables_forecast(self):
        result = CashFlowForecastingService.get_receivables_forecast(30)
        self.assertIn('total_pending', result)
        self.assertIn('invoices', result)

    def test_payables_forecast(self):
        result = CashFlowForecastingService.get_payables_forecast(30)
        self.assertIn('total_pending', result)
        self.assertIn('invoices', result)