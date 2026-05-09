"""
Advanced Reports Service - Inventory, Sales, Cash Book reports.
Provides detailed analysis and custom reporting capabilities.
"""
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from django.db.models import Sum, Avg, Count, Max, Min, Q, F
from django.db.models.functions import Coalesce
from django.utils import timezone


class AdvancedReportsService:
    """Service for generating advanced analytical reports."""
    
    @staticmethod
    def get_inventory_valuation(as_of_date: date = None, company_id: str = None) -> dict:
        """
        Generate inventory valuation report.
        Shows total stock value by product, category, warehouse.
        """
        from inventory.models import Product, Batch
        from core.multitenant.context import TenantContext
        
        if as_of_date is None:
            as_of_date = date.today()
        
        # Get company context
        if company_id is None:
            company_id = TenantContext.get_company_id()
        
        # Get active batches with remaining quantity
        queryset = Batch.objects.filter(
            remaining_quantity__gt=0,
            is_active=True,
            expiry_date__gte=as_of_date
        )
        
        if company_id:
            queryset = queryset.filter(company_id=company_id)
            products = Product.objects.filter(company_id=company_id, is_active=True)
        else:
            products = Product.objects.filter(is_active=True)
        
        # Group by product
        product_values = {}
        total_value = Decimal('0')
        total_items = 0
        
        for batch in queryset.select_related('product', 'product__category', 'warehouse'):
            product = batch.product
            product_id = str(product.id)
            
            if product_id not in product_values:
                product_values[product_id] = {
                    'product_id': product_id,
                    'product_code': product.sku or '',
                    'product_name': product.name,
                    'category': product.category.name if product.category else '',
                    'warehouse': batch.warehouse.name if batch.warehouse else '',
                    'total_quantity': 0,
                    'total_value': Decimal('0'),
                    'avg_cost': Decimal('0'),
                    'batches': []
                }
            
            # Calculate batch value (using purchase price or cost price)
            batch_value = batch.remaining_quantity * (batch.cost_price or Decimal('0'))
            
            product_values[product_id]['total_quantity'] += batch.remaining_quantity
            product_values[product_id]['total_value'] += batch_value
            product_values[product_id]['batches'].append({
                'batch_number': batch.batch_number,
                'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else '',
                'quantity': float(batch.remaining_quantity),
                'cost_price': float(batch.cost_price or 0),
                'value': float(batch_value)
            })
            
            total_value += batch_value
            total_items += 1
        
        # Calculate averages and build result
        results = []
        for pv in product_values.values():
            if pv['total_quantity'] > 0:
                pv['avg_cost'] = pv['total_value'] / pv['total_quantity']
                pv['total_quantity'] = float(pv['total_quantity'])
                pv['total_value'] = float(pv['total_value'])
                pv['avg_cost'] = float(pv['avg_cost'])
                results.append(pv)
        
        # Sort by value descending
        results.sort(key=lambda x: x['total_value'], reverse=True)
        
        return {
            'report_type': 'inventory_valuation',
            'as_of_date': as_of_date.isoformat(),
            'total_products': len(results),
            'total_items': total_items,
            'total_value': float(total_value),
            'products': results[:100],  # Limit to top 100
            'summary': {
                'by_category': AdvancedReportsService._summarize_by_category(results),
                'by_warehouse': AdvancedReportsService._summarize_by_warehouse(results)
            }
        }
    
    @staticmethod
    def _summarize_by_category(products: list) -> dict:
        """Summarize inventory by category."""
        categories = {}
        for p in products:
            cat = p.get('category', 'Uncategorized')
            if cat not in categories:
                categories[cat] = {'count': 0, 'value': 0, 'quantity': 0}
            categories[cat]['count'] += 1
            categories[cat]['value'] += p['total_value']
            categories[cat]['quantity'] += p['total_quantity']
        
        return [{'category': k, 'count': v['count'], 'value': float(v['value']), 'quantity': v['quantity']} 
                for k, v in categories.items()]
    
    @staticmethod
    def _summarize_by_warehouse(products: list) -> dict:
        """Summarize inventory by warehouse."""
        warehouses = {}
        for p in products:
            wh = p.get('warehouse', 'Unknown')
            if wh not in warehouses:
                warehouses[wh] = {'count': 0, 'value': 0, 'quantity': 0}
            warehouses[wh]['count'] += 1
            warehouses[wh]['value'] += p['total_value']
            warehouses[wh]['quantity'] += p['total_quantity']
        
        return [{'warehouse': k, 'count': v['count'], 'value': float(v['value']), 'quantity': v['quantity']} 
                for k, v in warehouses.items()]
    
    @staticmethod
    def get_sales_analysis(start_date: date, end_date: date, 
                          group_by: str = 'product', company_id: str = None) -> dict:
        """
        Sales analysis by product, customer, or category.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            group_by: 'product', 'customer', or 'category'
        """
        from sales.models import SalesInvoice, SalesItem
        from core.multitenant.context import TenantContext
        
        if company_id is None:
            company_id = TenantContext.get_company_id()
        
        # Get confirmed/paid invoices in period
        invoices = SalesInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['CONFIRMED', 'DISPATCHED', 'PAID', 'PARTIAL_PAID']
        )
        
        if company_id:
            invoices = invoices.filter(company_id=company_id)
        
        if group_by == 'product':
            return AdvancedReportsService._sales_by_product(invoices, start_date, end_date)
        elif group_by == 'customer':
            return AdvancedReportsService._sales_by_customer(invoices, start_date, end_date)
        elif group_by == 'category':
            return AdvancedReportsService._sales_by_category(invoices, start_date, end_date)
        else:
            return {'error': f'Invalid group_by: {group_by}'}
    
    @staticmethod
    def _sales_by_product(invoices, start_date, end_date):
        """Group sales by product."""
        from sales.models import SalesItem
        
        items = SalesItem.objects.filter(
            invoice__in=invoices
        ).select_related('product', 'product__category')
        
        products = {}
        total_revenue = Decimal('0')
        total_quantity = 0
        
        for item in items:
            pid = str(item.product.id)
            if pid not in products:
                products[pid] = {
                    'product_id': pid,
                    'product_code': item.product.sku or '',
                    'product_name': item.product.name,
                    'category': item.product.category.name if item.product.category else '',
                    'quantity_sold': 0,
                    'unit_price': float(item.unit_price),
                    'total_revenue': Decimal('0'),
                    'total_cost': Decimal('0'),
                    'discount': Decimal('0'),
                }
            
            products[pid]['quantity_sold'] += item.quantity
            products[pid]['total_revenue'] += item.total_price or Decimal('0')
            products[pid]['discount'] += item.discount or Decimal('0')
            
            total_revenue += item.total_price or Decimal('0')
            total_quantity += item.quantity
        
        # Calculate profit (simplified - would need cost data)
        results = list(products.values())
        results.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return {
            'report_type': 'sales_by_product',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_orders': invoices.count(),
            'total_revenue': float(total_revenue),
            'total_quantity': float(total_quantity),
            'top_products': results[:50]
        }
    
    @staticmethod
    def _sales_by_customer(invoices, start_date, end_date):
        """Group sales by customer."""
        customers = {}
        total_revenue = Decimal('0')
        
        for invoice in invoices.select_related('customer'):
            cid = str(invoice.customer.id) if invoice.customer else 'unknown'
            cname = invoice.customer.name if invoice.customer else 'Unknown'
            
            if cid not in customers:
                customers[cid] = {
                    'customer_id': cid,
                    'customer_name': cname,
                    'invoice_count': 0,
                    'total_revenue': Decimal('0'),
                    'total_quantity': 0,
                    'avg_invoice_value': Decimal('0'),
                }
            
            customers[cid]['invoice_count'] += 1
            customers[cid]['total_revenue'] += invoice.total_amount or Decimal('0')
            customers[cid]['total_quantity'] += invoice.items.count()
            total_revenue += invoice.total_amount or Decimal('0')
        
        # Calculate averages and build results
        results = []
        for c in customers.values():
            if c['invoice_count'] > 0:
                c['avg_invoice_value'] = c['total_revenue'] / c['invoice_count']
            c['total_revenue'] = float(c['total_revenue'])
            c['total_quantity'] = c['total_quantity']
            c['avg_invoice_value'] = float(c['avg_invoice_value'])
            results.append(c)
        
        results.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return {
            'report_type': 'sales_by_customer',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_customers': len(results),
            'total_revenue': float(total_revenue),
            'top_customers': results[:50]
        }
    
    @staticmethod
    def _sales_by_category(invoices, start_date, end_date):
        """Group sales by category."""
        from sales.models import SalesItem
        
        items = SalesItem.objects.filter(
            invoice__in=invoices
        ).select_related('product', 'product__category')
        
        categories = {}
        total_revenue = Decimal('0')
        
        for item in items:
            cat = item.product.category.name if item.product.category else 'Uncategorized'
            
            if cat not in categories:
                categories[cat] = {
                    'category': cat,
                    'product_count': 0,
                    'quantity_sold': 0,
                    'total_revenue': Decimal('0'),
                }
            
            categories[cat]['product_count'] += 1
            categories[cat]['quantity_sold'] += item.quantity
            categories[cat]['total_revenue'] += item.total_price or Decimal('0')
            total_revenue += item.total_price or Decimal('0')
        
        results = [{'category': k, 
                    'product_count': v['product_count'],
                    'quantity_sold': float(v['quantity_sold']),
                    'total_revenue': float(v['total_revenue'])} 
                   for k, v in categories.items()]
        results.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return {
            'report_type': 'sales_by_category',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_revenue': float(total_revenue),
            'categories': results
        }
    
    @staticmethod
    def get_cash_book(start_date: date, end_date: date, 
                      account_code: str = '1100', company_id: str = None) -> dict:
        """
        Cash Book report - shows all cash transactions.
        
        Args:
            start_date: Start date
            end_date: End date
            account_code: Cash account code (default: 1100)
        """
        from accounting.models import JournalEntry, JournalEntryLine, Account
        from core.multitenant.context import TenantContext
        
        if company_id is None:
            company_id = TenantContext.get_company_id()
        
        # Find cash account
        accounts = Account.objects.filter(code=account_code)
        if company_id:
            accounts = accounts.filter(company_id=company_id)
        
        cash_account = accounts.first()
        if not cash_account:
            return {'error': f'Cash account {account_code} not found'}
        
        # Get journal entries for cash account
        entries = JournalEntryLine.objects.filter(
            account=cash_account,
            journal_entry__entry_date__gte=start_date,
            journal_entry__entry_date__lte=end_date,
            journal_entry__is_posted=True
        ).select_related('journal_entry')
        
        if company_id:
            entries = entries.filter(journal_entry__company_id=company_id)
        
        # Build cash book
        opening_balance = Decimal('0')
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        transactions = []
        
        # Group by date
        for entry in entries.order_by('journal_entry__entry_date'):
            je = entry.journal_entry
            amount = entry.debit or Decimal('0') - (entry.credit or Decimal('0'))
            
            if amount > 0:
                total_debits += amount
            else:
                total_credits += abs(amount)
            
            transactions.append({
                'date': je.entry_date.isoformat(),
                'entry_number': je.entry_number,
                'description': je.description,
                'reference': je.reference or '',
                'entry_type': je.entry_type,
                'debit': float(entry.debit or 0),
                'credit': float(entry.credit or 0),
                'amount': float(amount),
            })
        
        closing_balance = opening_balance + total_debits - total_credits
        
        return {
            'report_type': 'cash_book',
            'account_code': account_code,
            'account_name': cash_account.name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'opening_balance': float(opening_balance),
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'closing_balance': float(closing_balance),
            'transactions': transactions,
            'summary': {
                'total_transactions': len(transactions),
                'by_type': AdvancedReportsService._summarize_by_entry_type(transactions)
            }
        }
    
    @staticmethod
    def _summarize_by_entry_type(transactions: list) -> dict:
        """Summarize cash book by entry type."""
        types = {}
        for t in transactions:
            et = t.get('entry_type', 'OTHER')
            if et not in types:
                types[et] = {'count': 0, 'debit': 0, 'credit': 0}
            types[et]['count'] += 1
            types[et]['debit'] += t.get('debit', 0)
            types[et]['credit'] += t.get('credit', 0)
        return types
    
    @staticmethod
    def get_purchase_analysis(start_date: date, end_date: date,
                               group_by: str = 'supplier', company_id: str = None) -> dict:
        """Purchase analysis by supplier or category."""
        from purchases.models import PurchaseInvoice, PurchaseItem
        from core.multitenant.context import TenantContext
        
        if company_id is None:
            company_id = TenantContext.get_company_id()
        
        invoices = PurchaseInvoice.objects.filter(
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
            status__in=['RECEIVED', 'PAID', 'CONFIRMED']
        )
        
        if company_id:
            invoices = invoices.filter(company_id=company_id)
        
        if group_by == 'supplier':
            return AdvancedReportsService._purchase_by_supplier(invoices, start_date, end_date)
        elif group_by == 'category':
            return AdvancedReportsService._purchase_by_category(invoices, start_date, end_date)
        
        return {'error': f'Invalid group_by: {group_by}'}
    
    @staticmethod
    def _purchase_by_supplier(invoices, start_date, end_date):
        """Group purchases by supplier."""
        suppliers = {}
        total_amount = Decimal('0')
        
        for invoice in invoices.select_related('supplier'):
            sid = str(invoice.supplier.id) if invoice.supplier else 'unknown'
            sname = invoice.supplier.name if invoice.supplier else 'Unknown'
            
            if sid not in suppliers:
                suppliers[sid] = {
                    'supplier_id': sid,
                    'supplier_name': sname,
                    'invoice_count': 0,
                    'total_amount': Decimal('0'),
                    'total_items': 0,
                }
            
            suppliers[sid]['invoice_count'] += 1
            suppliers[sid]['total_amount'] += invoice.total_amount or Decimal('0')
            suppliers[sid]['total_items'] += invoice.items.count()
            total_amount += invoice.total_amount or Decimal('0')
        
        results = [{'supplier_id': k,
                    'supplier_name': v['supplier_name'],
                    'invoice_count': v['invoice_count'],
                    'total_amount': float(v['total_amount']),
                    'total_items': v['total_items']} 
                   for k, v in suppliers.items()]
        results.sort(key=lambda x: x['total_amount'], reverse=True)
        
        return {
            'report_type': 'purchase_by_supplier',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_suppliers': len(results),
            'total_amount': float(total_amount),
            'top_suppliers': results[:30]
        }
    
    @staticmethod
    def _purchase_by_category(invoices, start_date, end_date):
        """Group purchases by category."""
        from purchases.models import PurchaseItem
        
        items = PurchaseItem.objects.filter(
            invoice__in=invoices
        ).select_related('product', 'product__category')
        
        categories = {}
        total_amount = Decimal('0')
        
        for item in items:
            cat = item.product.category.name if item.product.category else 'Uncategorized'
            
            if cat not in categories:
                categories[cat] = {
                    'category': cat,
                    'item_count': 0,
                    'total_quantity': 0,
                    'total_amount': Decimal('0'),
                }
            
            categories[cat]['item_count'] += 1
            categories[cat]['total_quantity'] += item.quantity
            categories[cat]['total_amount'] += (item.quantity * item.unit_price)
            total_amount += item.quantity * item.unit_price
        
        results = [{'category': k,
                    'item_count': v['item_count'],
                    'total_quantity': float(v['total_quantity']),
                    'total_amount': float(v['total_amount'])} 
                   for k, v in categories.items()]
        results.sort(key=lambda x: x['total_amount'], reverse=True)
        
        return {
            'report_type': 'purchase_by_category',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_amount': float(total_amount),
            'categories': results
        }


class ReportBuilderService:
    """Custom report builder service."""
    
    @staticmethod
    def build_custom_report(config: dict) -> dict:
        """
        Build custom report from configuration.
        
        config = {
            'report_name': 'My Report',
            'model': 'SalesInvoice' | 'PurchaseInvoice' | 'JournalEntry' | etc.
            'fields': ['field1', 'field2', ...],
            'filters': {'field': 'value', ...},
            'group_by': 'field_name',
            'aggregates': ['sum', 'count', 'avg'],
            'order_by': ['field1', '-field2'],
            'limit': 100
        }
        """
        from accounting.services.export_engine import ReportExporter
        
        model_name = config.get('model')
        fields = config.get('fields', [])
        filters = config.get('filters', {})
        
        # Map model names to Django models
        model_map = {
            'SalesInvoice': ('sales', 'SalesInvoice'),
            'PurchaseInvoice': ('purchases', 'PurchaseInvoice'),
            'Customer': ('sales', 'Customer'),
            'Supplier': ('purchases', 'Supplier'),
            'Product': ('inventory', 'Product'),
            'JournalEntry': ('accounting', 'JournalEntry'),
            'Account': ('accounting', 'Account'),
        }
        
        if model_name not in model_map:
            return {'error': f'Unknown model: {model_name}'}
        
        app_label, model_class = model_map[model_name]
        
        try:
            from django.apps import apps
            model = apps.get_model(app_label, model_class)
        except Exception as e:
            return {'error': str(e)}
        
        # Build queryset
        queryset = model.objects.filter(**filters)
        
        # Apply company filter if model has company field
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        if company_id and hasattr(model, 'company'):
            queryset = queryset.filter(company_id=company_id)
        
        # Get results
        results = []
        for obj in queryset[:config.get('limit', 100)]:
            row = {}
            for field in fields:
                value = getattr(obj, field, None)
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif hasattr(value, '__iter__') and not isinstance(value, str):
                    value = str(value)
                row[field] = value
            results.append(row)
        
        return {
            'report_type': 'custom',
            'report_name': config.get('report_name', 'Custom Report'),
            'model': model_name,
            'total_records': len(results),
            'fields': fields,
            'data': results
        }