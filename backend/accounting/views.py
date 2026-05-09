from decimal import Decimal
from datetime import date
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from accounting.services.invoice_calculator import InvoiceCalculator, InvoiceLineItem
from accounting.services.currency_converter import CurrencyConverter, CurrencyConversionError
from accounting.services.tax_calculator import TaxCalculator
from accounting.services.discount_calculator import DiscountCalculator
from accounting.models import Currency, ExchangeRate


class InvoiceCalculationRequestSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of items with quantity, unit_price, discount_type, discount_value, tax_rate, tax_type'
    )
    invoice_discount_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, default='0'
    )
    invoice_discount_type = serializers.ChoiceField(
        choices=['fixed', 'percentage'], default='fixed'
    )
    tax_rates = serializers.ListField(
        child=serializers.DecimalField(max_digits=5, decimal_places=2),
        required=False,
        allow_null=True
    )
    tax_type = serializers.ChoiceField(
        choices=['percentage', 'fixed', 'compound'], default='percentage'
    )
    use_compound_tax = serializers.BooleanField(default=False)
    currency_code = serializers.CharField(max_length=3, default='AFN')
    exchange_rate = serializers.DecimalField(
        max_digits=15, decimal_places=6, required=False, allow_null=True
    )
    exchange_date = serializers.DateField(required=False, allow_null=True)


@api_view(['POST'])
def calculate_invoice(request):
    """
    Calculate invoice totals with discounts, taxes, and currency conversion.
    
    Request body:
    {
        "items": [
            {"product_name": "Paracetamol", "quantity": 10, "unit_price": 50, "discount_value": 5, "discount_type": "percentage", "tax_rate": 4}
        ],
        "invoice_discount_value": 100,
        "invoice_discount_type": "fixed",
        "tax_rates": [4],
        "currency_code": "AFN"
    }
    """
    serializer = InvoiceCalculationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated = serializer.validated_data
    
    # Parse items
    items = []
    for item_data in validated['items']:
        items.append(InvoiceLineItem(
            product_name=item_data.get('product_name', ''),
            quantity=Decimal(str(item_data.get('quantity', 0))),
            unit_price=Decimal(str(item_data.get('unit_price', 0))),
            discount_type=item_data.get('discount_type', 'fixed'),
            discount_value=Decimal(str(item_data.get('discount_value', 0))),
            tax_rate=Decimal(str(item_data.get('tax_rate', 0))),
            tax_type=item_data.get('tax_type', 'percentage'),
        ))
    
    # Calculate
    calculator = InvoiceCalculator(
        currency_code=validated['currency_code'],
        exchange_rate=validated.get('exchange_rate'),
        exchange_date=validated.get('exchange_date')
    )
    
    result = calculator.calculate(
        items=items,
        invoice_discount_value=validated['invoice_discount_value'],
        invoice_discount_type=validated['invoice_discount_type'],
        tax_rates=validated.get('tax_rates'),
        tax_type=validated['tax_type'],
        use_compound_tax=validated['use_compound_tax']
    )
    
    return Response({
        'subtotal': result.subtotal,
        'item_discounts': result.item_discounts,
        'invoice_discount': result.invoice_discount,
        'total_discount': result.total_discount,
        'taxable_amount': result.taxable_amount,
        'tax': result.tax,
        'total': result.total,
        'currency': result.currency,
        'amount_in_base': result.amount_in_base,
        'exchange_rate': result.exchange_rate,
        'line_items': result.line_items,
        'discount_details': result.discount_details,
        'tax_details': result.tax_details,
        'warnings': result.warnings,
    })


@api_view(['POST'])
def convert_currency(request):
    """
    Convert amount between currencies.
    
    Request body:
    {
        "amount": 1000,
        "from_currency": "USD",
        "to_currency": "AFN",
        "effective_date": "2024-01-15"
    }
    """
    amount = request.data.get('amount')
    from_code = request.data.get('from_currency', 'AFN')
    to_code = request.data.get('to_currency', 'USD')
    effective_date_str = request.data.get('effective_date')
    
    if amount is None:
        return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from_currency = CurrencyConverter.get_currency(from_code)
        to_currency = CurrencyConverter.get_currency(to_code)
        effective_date = date.fromisoformat(effective_date_str) if effective_date_str else None
        
        result = CurrencyConverter.convert(
            Decimal(str(amount)), from_currency, to_currency, effective_date
        )
        
        return Response(result)
    except CurrencyConversionError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as e:
        return Response({'error': f'Invalid date format: {e}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_currencies(request):
    """Get all available currencies."""
    currencies = CurrencyConverter.get_available_currencies()
    return Response(currencies)


@api_view(['GET'])
def get_exchange_rates(request):
    """Get latest exchange rates."""
    from_code = request.query_params.get('from_currency')
    to_code = request.query_params.get('to_currency')
    
    from_currency = None
    to_currency = None
    
    if from_code:
        try:
            from_currency = CurrencyConverter.get_currency(from_code)
        except CurrencyConversionError:
            return Response({'error': f'Currency {from_code} not found'}, status=400)
    
    if to_code:
        try:
            to_currency = CurrencyConverter.get_currency(to_code)
        except CurrencyConversionError:
            return Response({'error': f'Currency {to_code} not found'}, status=400)
    
    rates = CurrencyConverter.get_latest_rates(from_currency, to_currency)
    return Response(rates)


@api_view(['POST'])
def calculate_mixed_payment(request):
    """
    Calculate total from mixed currency payments.
    
    Request body:
    {
        "payments": [
            {"amount": 5000, "currency_code": "AFN", "payment_method": "CASH"},
            {"amount": 50, "currency_code": "USD", "payment_method": "BANK_TRANSFER"}
        ],
        "to_currency": "AFN"
    }
    """
    payments = request.data.get('payments')
    if not payments:
        return Response({'error': 'Payments are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    to_code = request.data.get('to_currency')
    to_currency = CurrencyConverter.get_currency(to_code) if to_code else None
    
    effective_date_str = request.data.get('effective_date')
    effective_date = date.fromisoformat(effective_date_str) if effective_date_str else None
    
    try:
        result = CurrencyConverter.calculate_mixed_payment_total(
            payments, to_currency, effective_date
        )
        return Response(result)
    except CurrencyConversionError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def calculate_discount(request):
    """
    Calculate discount.
    
    Request body:
    {
        "type": "percentage",
        "value": 10,
        "subtotal": 5000
    }
    """
    discount_type = request.data.get('type', 'percentage')
    value = Decimal(str(request.data.get('value', 0)))
    subtotal = Decimal(str(request.data.get('subtotal', 0)))
    
    try:
        if discount_type == 'fixed':
            result = DiscountCalculator.calculate_fixed_discount(value, subtotal)
        elif discount_type == 'percentage':
            result = DiscountCalculator.calculate_percentage_discount(value, subtotal)
        elif discount_type == 'tiered':
            tiers = request.data.get('tiers', [])
            tiers = [(Decimal(str(t[0])), Decimal(str(t[1]))) for t in tiers]
            result = DiscountCalculator.calculate_tiered_discount(subtotal, tiers)
        else:
            return Response({'error': 'Invalid discount type'}, status=400)
        
        return Response({
            'discount_amount': result.discount_amount,
            'discount_type': result.discount_type,
            'discount_value': result.discount_value,
            'discount_description': result.discount_description,
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def calculate_tax(request):
    """
    Calculate tax.
    
    Request body:
    {
        "type": "percentage",
        "rate": 4,
        "amount": 5000,
        "is_compound": false
    }
    """
    tax_type = request.data.get('type', 'percentage')
    amount = Decimal(str(request.data.get('amount', 0)))
    
    try:
        if tax_type == 'percentage':
            rate = Decimal(str(request.data.get('rate', 0)))
            is_compound = request.data.get('is_compound', False)
            result = TaxCalculator.calculate_percentage_tax(rate, amount, is_compound)
        elif tax_type == 'fixed':
            result = TaxCalculator.calculate_fixed_tax(amount)
        elif tax_type == 'compound':
            rates = [Decimal(str(r)) for r in request.data.get('rates', [])]
            result = TaxCalculator.calculate_compound_tax(amount, rates)
        else:
            return Response({'error': 'Invalid tax type'}, status=400)
        
        return Response({
            'tax_amount': result.tax_amount,
            'tax_type': result.tax_type,
            'tax_rate': result.tax_rate,
            'tax_description': result.tax_description,
            'is_compound': result.is_compound,
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
