"""
Reporting Engine for Pharmacy ERP.
Read-only analytical layer for report generation.
Generates CSV, text, and structured data reports.
"""
import csv
import io
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, List
from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import TruncMonth

from sales.models import SalesInvoice, SalesItem, Customer
from purchases.models import PurchaseInvoice, PurchaseItem, Supplier
from inventory.models import Product, Batch, StockMovement, Warehouse
from accounting.models import Account, JournalEntry, JournalEntryLine

from analytics.services.costing import CostCenter, CostAggregator
from analytics.services.cashflow import CashFlowStatementGenerator
from analytics.services.profitability import (
    ProductProfitabilityAnalyzer,
    CustomerProfitabilityAnalyzer,
    SupplierProfitabilityAnalyzer,
)
from analytics.services.kpi import KPICalculator


class ReportGenerator:
    """
    Generates analytics reports in various formats.
    Read-only - does not modify any data.
    """

    @staticmethod
    def generate_cost_center_report(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'dict'
    ) -> str:
        """
        Generate cost center report.

        Args:
            start_date: Period start
            end_date: Period end
            format: Output format ('dict', 'csv', 'text')

        Returns:
            Report in requested format
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        data = CostAggregator.get_all_cost_centers_summary(start_date, end_date)

        if format == 'dict':
            return {
                'report_type': 'cost_center_summary',
                'period': {'start_date': start_date, 'end_date': end_date},
                'cost_centers': data,
            }
        elif format == 'csv':
            return ReportGenerator._to_csv_cost_center(data)
        elif format == 'text':
            return ReportGenerator._to_text_cost_center(data)
        return str(data)

    @staticmethod
    def _to_csv_cost_center(data: List[Dict]) -> str:
        """Convert cost center data to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Cost Center', 'Total Expenses'])
        for cc in data:
            writer.writerow([cc['cost_center_name'], cc['total_expenses']])
            for item in cc.get('breakdown', []):
                writer.writerow([f"  {item['account_name']}", item['amount']])
        return output.getvalue()

    @staticmethod
    def _to_text_cost_center(data: List[Dict]) -> str:
        """Convert cost center data to text."""
        lines = ['=' * 60, 'COST CENTER SUMMARY REPORT', '=' * 60, '']
        for cc in data:
            lines.append(f"{cc['cost_center_name']}: {cc['total_expenses']}")
            for item in cc.get('breakdown', []):
                lines.append(f"  {item['account_name']}: {item['amount']}")
            lines.append('')
        return '\n'.join(lines)

    @staticmethod
    def generate_cash_flow_report(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'dict'
    ) -> str:
        """Generate cash flow statement report."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        data = CashFlowStatementGenerator.generate_statement(start_date, end_date)

        if format == 'dict':
            return {
                'report_type': 'cash_flow_statement',
                'period': {'start_date': start_date, 'end_date': end_date},
                'statement': data,
            }
        elif format == 'text':
            return ReportGenerator._to_text_cash_flow(data)
        return str(data)

    @staticmethod
    def _to_text_cash_flow(data: Dict) -> str:
        """Convert cash flow data to text."""
        lines = ['=' * 60, 'CASH FLOW STATEMENT', '=' * 60, '']

        for section_key in ['operating_activities', 'investing_activities', 'financing_activities']:
            section = data.get(section_key, {})
            lines.append(f"{section.get('description', section_key)}:")
            lines.append(f"  Inflows: {section.get('total_inflows', 0)}")
            lines.append(f"  Outflows: {section.get('total_outflows', 0)}")
            lines.append(f"  Net: {section.get('net_cash', 0)}")
            lines.append('')

        lines.append(f"NET CASH FLOW: {data.get('net_cash_flow', 0)}")
        lines.append('=' * 60)
        return '\n'.join(lines)

    @staticmethod
    def generate_profitability_report(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'dict'
    ) -> str:
        """Generate profitability report."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        top_products = ProductProfitabilityAnalyzer.get_top_products(
            limit=20, start_date=start_date, end_date=end_date
        )
        top_customers = CustomerProfitabilityAnalyzer.get_top_customers(
            limit=20, start_date=start_date, end_date=end_date
        )

        if format == 'dict':
            return {
                'report_type': 'profitability_summary',
                'period': {'start_date': start_date, 'end_date': end_date},
                'top_products': top_products,
                'top_customers': top_customers,
            }
        elif format == 'csv':
            return ReportGenerator._to_csv_profitability(top_products, top_customers)
        return str({'products': top_products, 'customers': top_customers})

    @staticmethod
    def _to_csv_profitability(products: List[Dict], customers: List[Dict]) -> str:
        """Convert profitability data to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['PRODUCT PROFITABILITY'])
        writer.writerow(['Product', 'Revenue', 'COGS', 'Gross Profit', 'Margin %'])
        for p in products:
            writer.writerow([
                p['product_name'], p['net_revenue'], p['cost_of_goods_sold'],
                p['gross_profit'], p['gross_margin_pct']
            ])

        writer.writerow([])
        writer.writerow(['CUSTOMER PROFITABILITY'])
        writer.writerow(['Customer', 'Revenue', 'Paid', 'Outstanding', 'Invoices'])
        for c in customers:
            writer.writerow([
                c['customer_name'], c['net_revenue'], c['total_paid'],
                c['outstanding'], c['invoice_count']
            ])

        return output.getvalue()

    @staticmethod
    def generate_kpi_report(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'dict'
    ) -> str:
        """Generate KPI report."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        data = KPICalculator.get_all_kpis_summary(start_date, end_date)

        if format == 'dict':
            return {
                'report_type': 'kpi_summary',
                'period': {'start_date': start_date, 'end_date': end_date},
                'kpis': data,
            }
        elif format == 'text':
            return ReportGenerator._to_text_kpi(data)
        return str(data)

    @staticmethod
    def _to_text_kpi(data: Dict) -> str:
        """Convert KPI data to text."""
        lines = ['=' * 60, 'KEY PERFORMANCE INDICATORS', '=' * 60, '']

        profitability = data.get('profitability', {})
        gm = profitability.get('gross_margin', {})
        nm = profitability.get('net_margin', {})
        lines.append('PROFITABILITY:')
        lines.append(f"  Gross Margin: {gm.get('gross_margin_pct', 0)}%")
        lines.append(f"  Net Margin: {nm.get('net_margin_pct', 0)}%")
        lines.append('')

        efficiency = data.get('efficiency', {})
        it = efficiency.get('inventory_turnover', {})
        ccc = efficiency.get('cash_conversion_cycle', {})
        lines.append('EFFICIENCY:')
        lines.append(f"  Inventory Turnover: {it.get('inventory_turnover', 0)}")
        lines.append(f"  Days Sales of Inventory: {it.get('days_sales_of_inventory', 0)}")
        lines.append(f"  Cash Conversion Cycle: {ccc.get('cash_conversion_cycle', 0)} days")
        lines.append('')

        sales = data.get('sales', {})
        lines.append('SALES VELOCITY:')
        lines.append(f"  Total Revenue: {sales.get('total_revenue', 0)}")
        lines.append(f"  Average Order Value: {sales.get('average_order_value', 0)}")
        lines.append(f"  Daily Revenue: {sales.get('daily_revenue', 0)}")
        lines.append('')

        risk = data.get('risk', {})
        lines.append('RISK:')
        lines.append(f"  At-Risk Batches: {risk.get('at_risk_batch_count', 0)}")
        lines.append(f"  At-Risk Value: {risk.get('at_risk_value', 0)}")
        lines.append(f"  Expired Batches: {risk.get('expired_batch_count', 0)}")
        lines.append(f"  Total Risk Exposure: {risk.get('total_risk_exposure', 0)}")
        lines.append('=' * 60)
        return '\n'.join(lines)

    @staticmethod
    def generate_inventory_report(
        as_of_date: Optional[date] = None,
        format: str = 'dict'
    ) -> str:
        """Generate inventory status report."""
        if as_of_date is None:
            as_of_date = date.today()

        products = Product.objects.filter(is_active=True).select_related('category')

        inventory_data = []
        for product in products:
            batches = Batch.objects.filter(
                product=product, remaining_quantity__gt=0
            ).select_related('warehouse')

            total_qty = sum(b.remaining_quantity or Decimal('0') for b in batches)
            total_value = sum(
                (b.remaining_quantity or Decimal('0')) * (b.unit_price or Decimal('0'))
                for b in batches
            )

            expiring = batches.filter(
                expiry_date__lte=as_of_date + timedelta(days=90),
                expiry_date__gte=as_of_date
            ).count()

            inventory_data.append({
                'product_name': product.name,
                'product_code': product.code,
                'total_quantity': total_qty,
                'total_value': total_value.quantize(Decimal('0.01')),
                'batch_count': batches.count(),
                'expiring_90d': expiring,
            })

        if format == 'dict':
            return {
                'report_type': 'inventory_status',
                'as_of_date': as_of_date,
                'products': inventory_data,
            }
        elif format == 'csv':
            return ReportGenerator._to_csv_inventory(inventory_data)
        return str(inventory_data)

    @staticmethod
    def _to_csv_inventory(data: List[Dict]) -> str:
        """Convert inventory data to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Code', 'Quantity', 'Value', 'Batches', 'Expiring 90d'])
        for item in data:
            writer.writerow([
                item['product_name'], item['product_code'], item['total_quantity'],
                item['total_value'], item['batch_count'], item['expiring_90d']
            ])
        return output.getvalue()

    @staticmethod
    def generate_sales_report(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'dict'
    ) -> str:
        """Generate sales analysis report."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        invoices = SalesInvoice.objects.filter(
            order_date__gte=start_date,
            order_date__lte=end_date,
            status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True
        ).select_related('customer')

        total_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        total_discount = invoices.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        total_paid = invoices.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')

        sales_data = [
            {
                'invoice_number': inv.invoice_number,
                'customer': inv.customer.name,
                'order_date': inv.order_date,
                'total_amount': inv.total_amount,
                'paid_amount': inv.paid_amount,
                'balance': inv.total_amount - inv.paid_amount,
                'status': inv.status,
            }
            for inv in invoices
        ]

        if format == 'dict':
            return {
                'report_type': 'sales_analysis',
                'period': {'start_date': start_date, 'end_date': end_date},
                'summary': {
                    'total_revenue': total_revenue.quantize(Decimal('0.01')),
                    'total_discounts': total_discount.quantize(Decimal('0.01')),
                    'total_collected': total_paid.quantize(Decimal('0.01')),
                    'total_outstanding': (total_revenue - total_paid).quantize(Decimal('0.01')),
                    'invoice_count': invoices.count(),
                },
                'invoices': sales_data,
            }
        elif format == 'csv':
            return ReportGenerator._to_csv_sales(sales_data)
        return str(sales_data)

    @staticmethod
    def _to_csv_sales(data: List[Dict]) -> str:
        """Convert sales data to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Invoice', 'Customer', 'Date', 'Total', 'Paid', 'Balance', 'Status'])
        for item in data:
            writer.writerow([
                item['invoice_number'], item['customer'], item['order_date'],
                item['total_amount'], item['paid_amount'], item['balance'],
                item['status']
            ])
        return output.getvalue()

    @staticmethod
    def generate_comprehensive_report(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        format: str = 'dict'
    ) -> str:
        """
        Generate comprehensive report combining all analytics.

        Args:
            start_date: Period start
            end_date: Period end
            format: Output format ('dict', 'csv', 'text')

        Returns:
            Comprehensive analytics report
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        report = {
            'report_type': 'comprehensive_analytics',
            'generated_at': date.today().isoformat(),
            'period': {'start_date': start_date, 'end_date': end_date},
            'sections': {
                'cash_flow': ReportGenerator.generate_cash_flow_report(start_date, end_date, 'dict'),
                'profitability': ReportGenerator.generate_profitability_report(start_date, end_date, 'dict'),
                'kpi': ReportGenerator.generate_kpi_report(start_date, end_date, 'dict'),
                'inventory': ReportGenerator.generate_inventory_report(end_date, 'dict'),
                'sales': ReportGenerator.generate_sales_report(start_date, end_date, 'dict'),
            }
        }

        if format == 'text':
            return ReportGenerator._to_text_comprehensive(report)
        elif format == 'csv':
            return ReportGenerator._to_csv_comprehensive(report)
        return report

    @staticmethod
    def _to_text_comprehensive(report: Dict) -> str:
        """Convert comprehensive report to text."""
        lines = ['=' * 80, 'COMPREHENSIVE ANALYTICS REPORT', '=' * 80, '']
        lines.append(f"Period: {report['period']['start_date']} to {report['period']['end_date']}")
        lines.append(f"Generated: {report['generated_at']}")
        lines.append('')

        for section_name, section_data in report.get('sections', {}).items():
            lines.append('-' * 40)
            lines.append(section_name.upper())
            lines.append('-' * 40)

            if section_name == 'kpi':
                kpis = section_data.get('kpis', {})
                gm = kpis.get('profitability', {}).get('gross_margin', {})
                lines.append(f"Gross Margin: {gm.get('gross_margin_pct', 0)}%")
                nm = kpis.get('profitability', {}).get('net_margin', {})
                lines.append(f"Net Margin: {nm.get('net_margin_pct', 0)}%")
            elif section_name == 'sales':
                summary = section_data.get('summary', {})
                lines.append(f"Revenue: {summary.get('total_revenue', 0)}")
                lines.append(f"Invoices: {summary.get('invoice_count', 0)}")
            elif section_name == 'inventory':
                lines.append(f"Products: {len(section_data.get('products', []))}")

            lines.append('')

        lines.append('=' * 80)
        return '\n'.join(lines)

    @staticmethod
    def _to_csv_comprehensive(report: Dict) -> str:
        """Convert comprehensive report to CSV (combines all sections)."""
        output = io.StringIO()
        writer = csv.writer(output)

        sales = report.get('sections', {}).get('sales', {})
        if sales.get('invoices'):
            writer.writerow(['SALES'])
            writer.writerow(['Invoice', 'Customer', 'Date', 'Total', 'Paid', 'Balance', 'Status'])
            for inv in sales['invoices']:
                writer.writerow([
                    inv['invoice_number'], inv['customer'], inv['order_date'],
                    inv['total_amount'], inv['paid_amount'], inv['balance'], inv['status']
                ])
            writer.writerow([])

        inventory = report.get('sections', {}).get('inventory', {})
        if inventory.get('products'):
            writer.writerow(['INVENTORY'])
            writer.writerow(['Product', 'Code', 'Quantity', 'Value', 'Batches', 'Expiring'])
            for prod in inventory['products']:
                writer.writerow([
                    prod['product_name'], prod['product_code'], prod['total_quantity'],
                    prod['total_value'], prod['batch_count'], prod['expiring_90d']
                ])

        return output.getvalue()
