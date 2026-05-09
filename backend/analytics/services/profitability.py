"""
Profitability Engine for Pharmacy ERP.
Read-only analytical layer for profitability analysis.
Analyzes margins by product, warehouse, customer, and supplier.
"""
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, List
from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import TruncMonth

from sales.models import SalesInvoice, SalesItem, Customer
from purchases.models import PurchaseInvoice, PurchaseItem, Supplier
from inventory.models import Product, Warehouse, Batch


class ProductProfitabilityAnalyzer:
    """
    Analyzes profitability at the product level.
    Read-only - aggregates from sales and purchase data.
    """

    @staticmethod
    def analyze_product(
        product_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Calculate profitability for a single product.

        Args:
            product_id: Product UUID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Product profitability metrics
        """
        sales_filter = Q(product_id=product_id)
        if start_date:
            sales_filter &= Q(invoice__order_date__gte=start_date)
        if end_date:
            sales_filter &= Q(invoice__order_date__lte=end_date)
        sales_filter &= Q(invoice__status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'])
        sales_filter &= Q(invoice__is_active=True)

        sales_items = SalesItem.objects.filter(sales_filter).select_related('invoice', 'product')

        total_revenue = sales_items.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')

        total_discount = sales_items.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        net_revenue = total_revenue - total_discount

        total_quantity_sold = sales_items.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

        purchase_filter = Q(product_id=product_id)
        if start_date:
            purchase_filter &= Q(invoice__order_date__gte=start_date)
        if end_date:
            purchase_filter &= Q(invoice__order_date__lte=end_date)
        purchase_filter &= Q(invoice__status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'])
        purchase_filter &= Q(invoice__is_active=True)

        purchase_items = PurchaseItem.objects.filter(purchase_filter)

        total_cost = purchase_items.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')

        total_quantity_purchased = purchase_items.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

        avg_cost = (total_cost / total_quantity_purchased) if total_quantity_purchased > 0 else Decimal('0')
        cost_of_goods_sold = avg_cost * total_quantity_sold

        gross_profit = net_revenue - cost_of_goods_sold
        gross_margin = (gross_profit / net_revenue * Decimal('100')) if net_revenue > 0 else Decimal('0')

        product = Product.objects.filter(id=product_id).first()

        return {
            'product_id': product_id,
            'product_name': product.name if product else 'Unknown',
            'product_code': product.sku if product else '',
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'revenue': {
                'gross_revenue': total_revenue.quantize(Decimal('0.01')),
                'discounts': total_discount.quantize(Decimal('0.01')),
                'net_revenue': net_revenue.quantize(Decimal('0.01')),
            },
            'costs': {
                'total_purchase_cost': total_cost.quantize(Decimal('0.01')),
                'average_unit_cost': avg_cost.quantize(Decimal('0.01')),
                'cost_of_goods_sold': cost_of_goods_sold.quantize(Decimal('0.01')),
            },
            'profitability': {
                'gross_profit': gross_profit.quantize(Decimal('0.01')),
                'gross_margin_pct': gross_margin.quantize(Decimal('0.01')),
            },
            'volume': {
                'quantity_sold': total_quantity_sold,
                'quantity_purchased': total_quantity_purchased,
                'sales_transactions': sales_items.values('invoice').distinct().count(),
                'purchase_transactions': purchase_items.values('invoice').distinct().count(),
            }
        }

    @staticmethod
    def get_top_products(
        limit: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_by: str = 'gross_profit'
    ) -> List[Dict]:
        """
        Get top N products by profitability metric.

        Args:
            limit: Number of products to return
            start_date: Optional start date
            end_date: Optional end date
            sort_by: Metric to sort by ('gross_profit', 'gross_margin_pct', 'net_revenue')

        Returns:
            List of product profitability summaries
        """
        sales_filter = Q(invoice__status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'])
        sales_filter &= Q(invoice__is_active=True)
        if start_date:
            sales_filter &= Q(invoice__order_date__gte=start_date)
        if end_date:
            sales_filter &= Q(invoice__order_date__lte=end_date)

        product_stats = SalesItem.objects.filter(sales_filter).values(
            'product_id', 'product__name', 'product__sku'
        ).annotate(
            total_revenue=Sum('total'),
            total_discount=Sum('discount'),
            quantity_sold=Sum('quantity'),
            transaction_count=Count('invoice', distinct=True),
        ).order_by('-total_revenue')

        results = []
        for stat in product_stats:
            product_id = str(stat['product_id'])

            purchase_filter = Q(product_id=product_id)
            purchase_filter &= Q(invoice__status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'])
            purchase_filter &= Q(invoice__is_active=True)
            if start_date:
                purchase_filter &= Q(invoice__order_date__gte=start_date)
            if end_date:
                purchase_filter &= Q(invoice__order_date__lte=end_date)

            purchase_cost = PurchaseItem.objects.filter(purchase_filter).aggregate(
                total_cost=Sum('total'),
                total_qty=Sum('quantity')
            )

            total_purchase_cost = purchase_cost['total_cost'] or Decimal('0')
            total_purchase_qty = purchase_cost['total_qty'] or Decimal('0')
            avg_unit_cost = (total_purchase_cost / total_purchase_qty) if total_purchase_qty > 0 else Decimal('0')

            net_revenue = (stat['total_revenue'] or Decimal('0')) - (stat['total_discount'] or Decimal('0'))
            quantity_sold = stat['quantity_sold'] or Decimal('0')
            cogs = avg_unit_cost * quantity_sold
            gross_profit = net_revenue - cogs
            gross_margin = (gross_profit / net_revenue * Decimal('100')) if net_revenue > 0 else Decimal('0')

            results.append({
                'product_id': product_id,
                'product_name': stat['product__name'],
                'product_code': stat['product__sku'],
                'net_revenue': net_revenue.quantize(Decimal('0.01')),
                'cost_of_goods_sold': cogs.quantize(Decimal('0.01')),
                'gross_profit': gross_profit.quantize(Decimal('0.01')),
                'gross_margin_pct': gross_margin.quantize(Decimal('0.01')),
                'quantity_sold': quantity_sold,
            })

        sort_map = {
            'gross_profit': 'gross_profit',
            'gross_margin_pct': 'gross_margin_pct',
            'net_revenue': 'net_revenue',
        }
        sort_key = sort_map.get(sort_by, 'gross_profit')
        results.sort(key=lambda x: x[sort_key], reverse=True)

        return results[:limit]


class CustomerProfitabilityAnalyzer:
    """
    Analyzes profitability at the customer level.
    Read-only - aggregates from sales invoices and payments.
    """

    @staticmethod
    def analyze_customer(
        customer_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Calculate profitability for a single customer.

        Args:
            customer_id: Customer UUID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Customer profitability metrics
        """
        invoice_filter = Q(customer_id=customer_id)
        invoice_filter &= Q(status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'])
        invoice_filter &= Q(is_active=True)
        if start_date:
            invoice_filter &= Q(order_date__gte=start_date)
        if end_date:
            invoice_filter &= Q(order_date__lte=end_date)

        invoices = SalesInvoice.objects.filter(invoice_filter)

        total_revenue = invoices.aggregate(total=Sum('subtotal'))['total'] or Decimal('0')
        total_discount = invoices.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        total_tax = invoices.aggregate(total=Sum('tax'))['total'] or Decimal('0')
        net_revenue = total_revenue - total_discount

        total_paid = invoices.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')

        sales_items = SalesItem.objects.filter(invoice__in=invoices)

        product_ids = sales_items.values_list('product_id', flat=True).distinct()

        total_cogs = Decimal('0')
        for product_id in product_ids:
            product_items = sales_items.filter(product_id=product_id)
            qty_sold = product_items.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

            purchase_filter = Q(product_id=product_id)
            purchase_filter &= Q(invoice__status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'])
            purchase_filter &= Q(invoice__is_active=True)

            purchase_cost = PurchaseItem.objects.filter(purchase_filter).aggregate(
                total_cost=Sum(F('quantity') * F('unit_price')),
                total_qty=Sum('quantity')
            )

            total_purchase_cost = purchase_cost['total_cost'] or Decimal('0')
            total_purchase_qty = purchase_cost['total_qty'] or Decimal('0')
            avg_unit_cost = (total_purchase_cost / total_purchase_qty) if total_purchase_qty > 0 else Decimal('0')

            total_cogs += avg_unit_cost * qty_sold

        gross_profit = net_revenue - total_cogs
        gross_margin = (gross_profit / net_revenue * Decimal('100')) if net_revenue > 0 else Decimal('0')

        customer = Customer.objects.filter(id=customer_id).first()

        return {
            'customer_id': customer_id,
            'customer_name': customer.name if customer else 'Unknown',
            'customer_code': customer.code if customer else '',
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'revenue': {
                'gross_revenue': total_revenue.quantize(Decimal('0.01')),
                'discounts': total_discount.quantize(Decimal('0.01')),
                'net_revenue': net_revenue.quantize(Decimal('0.01')),
                'total_tax_collected': total_tax.quantize(Decimal('0.01')),
            },
            'costs': {
                'cost_of_goods_sold': total_cogs.quantize(Decimal('0.01')),
            },
            'profitability': {
                'gross_profit': gross_profit.quantize(Decimal('0.01')),
                'gross_margin_pct': gross_margin.quantize(Decimal('0.01')),
            },
            'payments': {
                'total_paid': total_paid.quantize(Decimal('0.01')),
                'outstanding_balance': (net_revenue - total_paid).quantize(Decimal('0.01')),
            },
            'volume': {
                'total_invoices': invoices.count(),
                'total_items_sold': sales_items.aggregate(total=Sum('quantity'))['total'] or Decimal('0'),
            }
        }

    @staticmethod
    def get_top_customers(
        limit: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """Get top N customers by revenue."""
        invoice_filter = Q(status__in=['DISPATCHED', 'PARTIAL_PAID', 'PAID'])
        invoice_filter &= Q(is_active=True)
        if start_date:
            invoice_filter &= Q(order_date__gte=start_date)
        if end_date:
            invoice_filter &= Q(order_date__lte=end_date)

        customers = SalesInvoice.objects.filter(invoice_filter).values(
            'customer_id', 'customer__name', 'customer__code'
        ).annotate(
            net_revenue=Sum('subtotal') - Sum('discount'),
            total_paid=Sum('paid_amount'),
            invoice_count=Count('id', distinct=True),
        ).order_by('-net_revenue')[:limit]

        return [
            {
                'customer_id': str(item['customer_id']),
                'customer_name': item['customer__name'],
                'customer_code': item['customer__code'],
                'net_revenue': (item['net_revenue'] or Decimal('0')).quantize(Decimal('0.01')),
                'total_paid': (item['total_paid'] or Decimal('0')).quantize(Decimal('0.01')),
                'outstanding': ((item['net_revenue'] or Decimal('0')) - (item['total_paid'] or Decimal('0'))).quantize(Decimal('0.01')),
                'invoice_count': item['invoice_count'],
            }
            for item in customers
        ]


class SupplierProfitabilityAnalyzer:
    """
    Analyzes supplier cost efficiency.
    Read-only - aggregates from purchase invoices.
    """

    @staticmethod
    def analyze_supplier(
        supplier_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Analyze supplier cost efficiency.

        Args:
            supplier_id: Supplier UUID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Supplier cost efficiency metrics
        """
        invoice_filter = Q(supplier_id=supplier_id)
        invoice_filter &= Q(status__in=['RECEIVED', 'PARTIAL_PAID', 'PAID'])
        invoice_filter &= Q(is_active=True)
        if start_date:
            invoice_filter &= Q(order_date__gte=start_date)
        if end_date:
            invoice_filter &= Q(order_date__lte=end_date)

        invoices = PurchaseInvoice.objects.filter(invoice_filter)

        total_cost = invoices.aggregate(total=Sum('subtotal'))['total'] or Decimal('0')
        total_discount = invoices.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        total_tax = invoices.aggregate(total=Sum('tax'))['total'] or Decimal('0')
        net_cost = total_cost - total_discount

        total_paid = invoices.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')

        purchase_items = PurchaseItem.objects.filter(invoice__in=invoices)

        supplier = Supplier.objects.filter(id=supplier_id).first()

        return {
            'supplier_id': supplier_id,
            'supplier_name': supplier.name if supplier else 'Unknown',
            'supplier_code': supplier.code if supplier else '',
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'costs': {
                'gross_cost': total_cost.quantize(Decimal('0.01')),
                'discounts_received': total_discount.quantize(Decimal('0.01')),
                'net_cost': net_cost.quantize(Decimal('0.01')),
                'total_tax_paid': total_tax.quantize(Decimal('0.01')),
            },
            'payments': {
                'total_paid': total_paid.quantize(Decimal('0.01')),
                'outstanding_balance': (net_cost - total_paid).quantize(Decimal('0.01')),
            },
            'volume': {
                'total_invoices': invoices.count(),
                'total_items_purchased': purchase_items.aggregate(total=Sum('quantity'))['total'] or Decimal('0'),
                'unique_products': purchase_items.values('product_id').distinct().count(),
            }
        }


class WarehouseProfitabilityAnalyzer:
    """
    Analyzes profitability by warehouse.
    Read-only - aggregates from inventory and sales data.
    """

    @staticmethod
    def analyze_warehouse(
        warehouse_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Analyze warehouse profitability.

        Args:
            warehouse_id: Warehouse UUID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Warehouse profitability metrics
        """
        from inventory.models import StockMovement

        stock_filter = Q(warehouse_id=warehouse_id)
        if start_date:
            stock_filter &= Q(created_at__date__gte=start_date)
        if end_date:
            stock_filter &= Q(created_at__date__lte=end_date)

        movements_in = StockMovement.objects.filter(stock_filter, movement_type='IN')
        movements_out = StockMovement.objects.filter(stock_filter, movement_type='OUT')

        total_quantity_in = movements_in.aggregate(total=Sum('quantity'))['total'] or Decimal('0')
        total_quantity_out = movements_out.aggregate(total=Sum('quantity'))['total'] or Decimal('0')

        warehouse_revenue = Decimal('0')

        warehouse = Warehouse.objects.filter(id=warehouse_id).first()

        return {
            'warehouse_id': warehouse_id,
            'warehouse_name': warehouse.name if warehouse else 'Unknown',
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'inventory': {
                'quantity_in': total_quantity_in,
                'quantity_out': total_quantity_out,
                'current_stock': total_quantity_in - total_quantity_out,
            },
            'revenue': {
                'warehouse_revenue': warehouse_revenue.quantize(Decimal('0.01')),
            },
            'volume': {
                'inbound_movements': movements_in.count(),
                'outbound_movements': movements_out.count(),
            }
        }
