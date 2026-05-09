from decimal import Decimal
from datetime import date
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from accounting.models import Account, Currency
from entities.models import Entity, EntityAccount, InterCompanyTransaction
from entities.services.entity_service import EntityService
from entities.services.consolidated_reporting import ConsolidatedReportingService



class EntityModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.account = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', 
            account_category='CURRENT_ASSET', is_active=True
        )

    def test_create_entity(self):
        entity = Entity.objects.create(
            name='Main Pharmacy', code='PH001', entity_type='PHARMACY',
            base_currency=self.currency, is_default=True
        )
        self.assertEqual(entity.code, 'PH001')
        self.assertTrue(entity.is_default)

    def test_unique_default_entity(self):
        Entity.objects.create(name='First', code='E1', entity_type='HEADQUARTER', is_default=True)
        with self.assertRaises(Exception):
            Entity.objects.create(name='Second', code='E2', entity_type='PHARMACY', is_default=True)

    def test_entity_str(self):
        entity = Entity.objects.create(name='Test', code='T1', entity_type='PHARMACY')
        self.assertEqual(str(entity), 'T1 - Test')


class EntityServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.entity = Entity.objects.create(name='Test', code='T1', entity_type='PHARMACY')
        cls.account = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET',
            account_category='CURRENT_ASSET', is_active=True
        )

    def test_add_entity_account(self):
        ea = EntityService.add_entity_account(self.entity, self.account, 'Main Cash')
        self.assertEqual(ea.account_name, 'Main Cash')
        self.assertTrue(ea.is_active)

    def test_get_entity_accounts(self):
        EntityService.add_entity_account(self.entity, self.account)
        accounts = EntityService.get_entity_accounts(self.entity)
        self.assertEqual(len(accounts), 1)


class ConsolidatedReportingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.entity1 = Entity.objects.create(name='Pharmacy 1', code='P1', entity_type='PHARMACY')
        cls.entity2 = Entity.objects.create(name='Pharmacy 2', code='P2', entity_type='PHARMACY')
        cls.asset = Account.objects.create(code='1000', name='Cash', account_type='ASSET', account_category='CURRENT_ASSET', is_active=True)
        cls.revenue = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', account_category='OPERATING_REVENUE', is_active=True)

    def test_consolidated_balance_sheet(self):
        result = ConsolidatedReportingService.get_consolidated_balance_sheet(date.today())
        self.assertIn('assets', result)
        self.assertIn('liabilities', result)
        self.assertIn('equity', result)

    def test_consolidated_cash_flow(self):
        result = ConsolidatedReportingService.get_consolidated_cash_flow(date(2024,1,1), date(2024,12,31))
        self.assertIn('opening_cash', result)
        self.assertIn('closing_cash', result)

    def test_entity_performance_summary(self):
        result = ConsolidatedReportingService.get_entity_performance_summary(date(2024,1,1), date(2024,12,31))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['entity_code'], 'P1')


class InterCompanyTransactionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)
        cls.e1 = Entity.objects.create(name='Entity 1', code='E1', entity_type='PHARMACY')
        cls.e2 = Entity.objects.create(name='Entity 2', code='E2', entity_type='WAREHOUSE')

    def test_create_inter_company_tx(self):
        tx = InterCompanyTransaction.objects.create(
            from_entity=self.e1, to_entity=self.e2,
            transaction_type='TRANSFER', amount=Decimal('1000.00'),
            currency=self.currency, transaction_date=date.today()
        )
        self.assertEqual(tx.amount, Decimal('1000.00'))
        self.assertFalse(tx.is_reconciled)

    def test_reconcile_transaction(self):
        tx = InterCompanyTransaction.objects.create(
            from_entity=self.e1, to_entity=self.e2,
            transaction_type='TRANSFER', amount=Decimal('500.00'),
            currency=self.currency, transaction_date=date.today()
        )
        tx = EntityService.reconcile_transaction(tx)
        self.assertTrue(tx.is_reconciled)