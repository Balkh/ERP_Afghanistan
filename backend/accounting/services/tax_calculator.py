from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class TaxType(str, Enum):
    FIXED = 'fixed'
    PERCENTAGE = 'percentage'
    COMPOUND = 'compound'
    EXEMPT = 'exempt'


@dataclass
class TaxResult:
    tax_amount: Decimal
    tax_type: str
    tax_rate: Decimal
    tax_description: str
    is_compound: bool = False


class TaxCalculator:
    """
    Handles all tax calculations for invoices.
    Supports fixed, percentage, compound, and exempt tax types.
    """

    @staticmethod
    def calculate_percentage_tax(
        rate: Decimal,
        taxable_amount: Decimal,
        is_compound: bool = False
    ) -> TaxResult:
        """
        Calculate percentage-based tax.
        
        Args:
            rate: Tax rate percentage (e.g., 10 for 10%)
            taxable_amount: Amount to apply tax to
            is_compound: Whether this tax is compound (tax on tax)
            
        Returns:
            TaxResult with calculated tax
        """
        if rate < 0:
            raise ValueError('Tax rate cannot be negative.')
        
        if taxable_amount < 0:
            raise ValueError('Taxable amount cannot be negative.')
        
        tax_amount = (taxable_amount * rate / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return TaxResult(
            tax_amount=tax_amount,
            tax_type=TaxType.PERCENTAGE,
            tax_rate=rate,
            tax_description=f'{rate}% tax on {taxable_amount}',
            is_compound=is_compound
        )

    @staticmethod
    def calculate_fixed_tax(
        amount: Decimal
    ) -> TaxResult:
        """
        Calculate fixed tax amount.
        
        Args:
            amount: Fixed tax amount
            
        Returns:
            TaxResult with calculated tax
        """
        if amount < 0:
            raise ValueError('Fixed tax amount cannot be negative.')
        
        return TaxResult(
            tax_amount=amount,
            tax_type=TaxType.FIXED,
            tax_rate=Decimal('0'),
            tax_description=f'Fixed tax: {amount}'
        )

    @staticmethod
    def calculate_item_level_taxes(
        items: list[dict],
        default_tax_rate: Optional[Decimal] = None
    ) -> tuple[Decimal, list[dict]]:
        """
        Calculate taxes at the item level.
        
        Args:
            items: List of item dicts with keys:
                   - quantity
                   - unit_price
                   - tax_rate (optional)
                   - tax_type (optional: 'percentage', 'fixed', 'exempt')
            default_tax_rate: Default tax rate if not specified on item
            
        Returns:
            Tuple of (total_tax_amount, updated_items)
        """
        total_tax = Decimal('0')
        updated_items = []
        
        for item in items:
            quantity = Decimal(str(item['quantity']))
            unit_price = Decimal(str(item['unit_price']))
            line_total = quantity * unit_price
            
            tax_type = item.get('tax_type', 'percentage')
            
            if tax_type == 'exempt':
                item_tax = Decimal('0')
                tax_rate = Decimal('0')
            elif tax_type == 'fixed':
                item_tax = Decimal(str(item.get('tax_amount', 0))) * quantity
                tax_rate = Decimal('0')
            else:
                # Percentage tax
                tax_rate = Decimal(str(item.get('tax_rate', default_tax_rate or 0)))
                item_tax = (line_total * tax_rate / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            
            total_tax += item_tax
            
            updated_item = item.copy()
            updated_item['line_total'] = line_total
            updated_item['item_tax'] = item_tax
            updated_item['line_total_after_tax'] = line_total + item_tax
            updated_items.append(updated_item)
        
        return total_tax, updated_items

    @staticmethod
    def calculate_compound_tax(
        base_amount: Decimal,
        tax_rates: list[Decimal]
    ) -> TaxResult:
        """
        Calculate compound tax (tax applied sequentially).
        
        Args:
            base_amount: Amount to apply taxes to
            tax_rates: List of tax rates to apply sequentially
            
        Returns:
            TaxResult with calculated tax
        """
        if base_amount < 0:
            raise ValueError('Base amount cannot be negative.')
        
        current_amount = base_amount
        total_tax = Decimal('0')
        descriptions = []
        
        for rate in tax_rates:
            if rate < 0:
                raise ValueError('Tax rate cannot be negative.')
            
            tax = (current_amount * rate / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            total_tax += tax
            current_amount += tax
            descriptions.append(f'{rate}%')
        
        return TaxResult(
            tax_amount=total_tax,
            tax_type=TaxType.COMPOUND,
            tax_rate=sum(tax_rates),
            tax_description=f'Compound tax ({", ".join(descriptions)}) on {base_amount}',
            is_compound=True
        )

    @staticmethod
    def calculate_multi_tax(
        taxable_amount: Decimal,
        taxes: list[dict]
    ) -> tuple[Decimal, list[TaxResult]]:
        """
        Calculate multiple taxes on the same amount.
        
        Args:
            taxable_amount: Amount to apply taxes to
            taxes: List of tax dicts with keys:
                   - rate
                   - type ('percentage', 'fixed', 'compound')
                   - amount (for fixed)
                   - is_compound (for percentage)
        
        Returns:
            Tuple of (total_tax_amount, list of TaxResult)
        """
        if taxable_amount < 0:
            raise ValueError('Taxable amount cannot be negative.')
        
        total_tax = Decimal('0')
        results = []
        
        for tax_def in taxes:
            tax_type = tax_def.get('type', 'percentage')
            
            if tax_type == 'fixed':
                result = TaxCalculator.calculate_fixed_tax(
                    Decimal(str(tax_def['amount']))
                )
            elif tax_type == 'compound':
                rates = [Decimal(str(r)) for r in tax_def.get('rates', [])]
                result = TaxCalculator.calculate_compound_tax(taxable_amount, rates)
            else:
                result = TaxCalculator.calculate_percentage_tax(
                    rate=Decimal(str(tax_def.get('rate', 0))),
                    taxable_amount=taxable_amount,
                    is_compound=tax_def.get('is_compound', False)
                )
            
            total_tax += result.tax_amount
            results.append(result)
        
        return total_tax, results

    @staticmethod
    def calculate_afghanistan_business_tax(
        amount: Decimal
    ) -> TaxResult:
        """
        Calculate Afghanistan Business Receipts Tax (BRT).
        Default rate is 4% for goods, 10% for services.
        
        Args:
            amount: Taxable amount
            
        Returns:
            TaxResult with calculated tax
        """
        # Default to 4% for goods (pharmacy)
        rate = Decimal('4')
        return TaxCalculator.calculate_percentage_tax(rate, amount)
