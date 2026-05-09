from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dataclasses import dataclass, field
from typing import Optional

from accounting.services.discount_calculator import DiscountCalculator, DiscountResult
from accounting.services.tax_calculator import TaxCalculator, TaxResult
from accounting.services.currency_converter import CurrencyConverter, CurrencyConversionError
from accounting.models import Currency


@dataclass
class InvoiceLineItem:
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount_type: str = 'fixed'
    discount_value: Decimal = Decimal('0')
    tax_rate: Decimal = Decimal('0')
    tax_type: str = 'percentage'


@dataclass
class InvoiceCalculationResult:
    subtotal: Decimal = Decimal('0')
    item_discounts: Decimal = Decimal('0')
    invoice_discount: Decimal = Decimal('0')
    total_discount: Decimal = Decimal('0')
    taxable_amount: Decimal = Decimal('0')
    tax: Decimal = Decimal('0')
    total: Decimal = Decimal('0')
    currency: str = 'AFN'
    amount_in_base: Decimal = Decimal('0')
    exchange_rate: Decimal = Decimal('1')
    line_items: list = field(default_factory=list)
    discount_details: list = field(default_factory=list)
    tax_details: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class InvoiceCalculator:
    """
    Main invoice calculation engine.
    
    Handles:
    - Line item calculations
    - Item-level discounts
    - Invoice-level discounts
    - Tax calculations (percentage, fixed, compound)
    - Currency conversion
    - Mixed payment calculations
    """

    def __init__(
        self,
        currency_code: str = 'AFN',
        exchange_rate: Optional[Decimal] = None,
        exchange_date: Optional[date] = None
    ):
        self.currency_code = currency_code
        self.exchange_rate = exchange_rate
        self.exchange_date = exchange_date
        self.currency = CurrencyConverter.get_currency(currency_code)
        self.base_currency = CurrencyConverter.get_base_currency()

    def calculate(
        self,
        items: list[InvoiceLineItem],
        invoice_discount_value: Decimal = Decimal('0'),
        invoice_discount_type: str = 'fixed',
        tax_rates: Optional[list[Decimal]] = None,
        tax_type: str = 'percentage',
        use_compound_tax: bool = False
    ) -> InvoiceCalculationResult:
        """
        Calculate complete invoice totals.
        
        Args:
            items: List of InvoiceLineItem objects
            invoice_discount_value: Invoice-level discount value
            invoice_discount_type: 'fixed' or 'percentage'
            tax_rates: List of tax rates to apply
            tax_type: 'percentage', 'fixed', or 'compound'
            use_compound_tax: Whether to apply taxes compoundly
            
        Returns:
            InvoiceCalculationResult with all calculations
        """
        result = InvoiceCalculationResult(currency=self.currency_code)
        
        # Step 1: Calculate line items
        subtotal = Decimal('0')
        line_item_results = []
        
        for item in items:
            line_total = item.quantity * item.unit_price
            
            # Item-level discount
            item_discount = Decimal('0')
            if item.discount_type == 'fixed':
                item_discount = item.discount_value * item.quantity
            elif item.discount_type == 'percentage':
                item_discount = (line_total * item.discount_value / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            
            line_after_discount = line_total - item_discount
            
            # Item-level tax
            item_tax = Decimal('0')
            if item.tax_type == 'percentage':
                item_tax = (line_after_discount * item.tax_rate / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            elif item.tax_type == 'fixed':
                item_tax = item.tax_rate * item.quantity
            
            line_after_tax = line_after_discount + item_tax
            subtotal += line_after_discount
            
            line_item_results.append({
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'line_total': line_total,
                'item_discount': item_discount,
                'line_after_discount': line_after_discount,
                'item_tax': item_tax,
                'line_total_with_tax': line_after_tax,
            })
        
        result.subtotal = subtotal
        result.line_items = line_item_results
        
        # Step 2: Apply invoice-level discount
        if invoice_discount_value > 0:
            if invoice_discount_type == 'fixed':
                discount_result = DiscountCalculator.calculate_fixed_discount(
                    invoice_discount_value, subtotal
                )
            else:
                discount_result = DiscountCalculator.calculate_percentage_discount(
                    invoice_discount_value, subtotal
                )
            
            result.invoice_discount = discount_result.discount_amount
            result.discount_details.append({
                'type': discount_result.discount_type,
                'value': discount_result.discount_value,
                'amount': discount_result.discount_amount,
                'description': discount_result.discount_description,
            })
        
        # Total discounts
        total_item_discounts = sum(
            Decimal(str(li['item_discount'])) for li in line_item_results
        )
        result.item_discounts = total_item_discounts
        result.total_discount = total_item_discounts + result.invoice_discount
        
        # Step 3: Calculate taxable amount
        result.taxable_amount = subtotal - result.invoice_discount
        
        # Step 4: Apply taxes
        if tax_rates and len(tax_rates) > 0:
            if use_compound_tax and len(tax_rates) > 1:
                tax_result = TaxCalculator.calculate_compound_tax(
                    result.taxable_amount, tax_rates
                )
                result.tax = tax_result.tax_amount
                result.tax_details.append({
                    'type': tax_result.tax_type,
                    'rates': tax_rates,
                    'amount': tax_result.tax_amount,
                    'description': tax_result.tax_description,
                    'is_compound': True,
                })
            else:
                total_tax = Decimal('0')
                for rate in tax_rates:
                    tax_result = TaxCalculator.calculate_percentage_tax(
                        rate, result.taxable_amount
                    )
                    total_tax += tax_result.tax_amount
                    result.tax_details.append({
                        'type': tax_result.tax_type,
                        'rate': rate,
                        'amount': tax_result.tax_amount,
                        'description': tax_result.tax_description,
                        'is_compound': False,
                    })
                result.tax = total_tax
        
        # Step 5: Calculate total
        result.total = result.taxable_amount + result.tax
        
        # Step 6: Currency conversion
        if self.currency != self.base_currency:
            try:
                conversion = CurrencyConverter.convert(
                    result.total,
                    self.currency,
                    self.base_currency,
                    self.exchange_date,
                    self.exchange_rate
                )
                result.amount_in_base = conversion['converted_amount']
                result.exchange_rate = conversion['rate_used']
            except CurrencyConversionError as e:
                result.warnings.append(f'Currency conversion failed: {str(e)}')
                result.amount_in_base = result.total
                result.exchange_rate = Decimal('1')
        else:
            result.amount_in_base = result.total
            result.exchange_rate = Decimal('1')
        
        return result

    def calculate_simple(
        self,
        items: list[dict],
        discount: Decimal = Decimal('0'),
        tax_rate: Decimal = Decimal('0'),
        currency_code: str = 'AFN'
    ) -> dict:
        """
        Simple calculation for quick estimates.
        
        Args:
            items: List of dicts with 'quantity', 'unit_price'
            discount: Total discount amount
            tax_rate: Tax percentage
            currency_code: Currency code
            
        Returns:
            Dict with calculation results
        """
        subtotal = sum(
            Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))
            for item in items
        )
        
        after_discount = subtotal - discount
        tax = (after_discount * tax_rate / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        total = after_discount + tax
        
        return {
            'subtotal': subtotal,
            'discount': discount,
            'after_discount': after_discount,
            'tax_rate': tax_rate,
            'tax': tax,
            'total': total,
            'currency': currency_code,
            'item_count': len(items),
        }

    def calculate_mixed_payment_invoice(
        self,
        items: list[InvoiceLineItem],
        payments: list[dict],
        invoice_discount_value: Decimal = Decimal('0'),
        invoice_discount_type: str = 'fixed',
        tax_rates: Optional[list[Decimal]] = None
    ) -> dict:
        """
        Calculate invoice with mixed currency payments.
        
        Args:
            items: Invoice line items
            payments: List of payment dicts with 'amount', 'currency_code', 'payment_method'
            invoice_discount_value: Invoice discount
            invoice_discount_type: Discount type
            tax_rates: Tax rates
            
        Returns:
            Dict with invoice total and payment reconciliation
        """
        # Calculate invoice
        invoice_result = self.calculate(
            items, invoice_discount_value, invoice_discount_type, tax_rates
        )
        
        # Calculate mixed payment total
        payment_total = CurrencyConverter.calculate_mixed_payment_total(
            payments,
            to_currency=self.currency,
            effective_date=self.exchange_date
        )
        
        # Calculate remaining balance
        remaining = invoice_result.total - payment_total['total']
        
        return {
            'invoice': {
                'subtotal': invoice_result.subtotal,
                'total_discount': invoice_result.total_discount,
                'tax': invoice_result.tax,
                'total': invoice_result.total,
                'currency': invoice_result.currency,
            },
            'payments': payment_total,
            'remaining_balance': max(Decimal('0'), remaining),
            'overpayment': max(Decimal('0'), -remaining),
            'is_fully_paid': remaining <= 0,
        }
