"""Returns API Serializers."""
from decimal import Decimal
from rest_framework import serializers
from .models import ReturnOrder, ReturnItem, ReconciliationEntry


class ReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    
    class Meta:
        model = ReturnItem
        fields = [
            'id', 'product', 'product_name', 'batch', 'batch_number',
            'return_quantity', 'unit_price', 'total_price', 'notes'
        ]


class ReturnOrderSerializer(serializers.ModelSerializer):
    items = ReturnItemSerializer(many=True, read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    purchase_invoice_number = serializers.CharField(source='purchase_invoice.invoice_number', read_only=True)
    party_name = serializers.CharField(source='party.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.first_name', read_only=True)
    
    class Meta:
        model = ReturnOrder
        fields = [
            'id', 'return_number', 'return_type', 'invoice', 'invoice_number',
            'purchase_invoice', 'purchase_invoice_number', 'party', 'party_name',
            'supplier', 'supplier_name', 'status', 'total_amount', 'reason',
            'notes', 'approved_by', 'approved_by_name', 'approved_at',
            'credit_note_number', 'journal_entry', 'items', 'created_at', 'updated_at'
        ]


class ReturnOrderCreateSerializer(serializers.ModelSerializer):
    items = ReturnItemSerializer(many=True)
    
    class Meta:
        model = ReturnOrder
        fields = [
            'return_type', 'invoice', 'purchase_invoice', 'party', 'supplier',
            'reason', 'notes', 'items'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        return_order = ReturnOrder.objects.create(**validated_data)
        
        total_amount = Decimal('0.00')
        for item_data in items_data:
            # Auto-calculate proportional discount and tax from original invoice item
            prod = item_data['product']
            qty = item_data['return_quantity']
            
            discount = Decimal('0.00')
            tax = Decimal('0.00')
            unit_price = item_data.get('unit_price')
            
            if return_order.return_type == 'SALE_RETURN' and return_order.invoice:
                from sales.models import SalesItem
                inv_item = SalesItem.objects.filter(invoice=return_order.invoice, product=prod).first()
                if inv_item:
                    # Proportional calculation
                    prop = qty / inv_item.quantity
                    discount = (inv_item.discount * prop).quantize(Decimal('0.01'))
                    tax = (inv_item.tax * prop).quantize(Decimal('0.01'))
                    unit_price = inv_item.unit_price
                    item_data['invoice_item'] = inv_item
            
            elif return_order.return_type == 'PURCHASE_RETURN' and return_order.purchase_invoice:
                from purchases.models import PurchaseItem
                pur_item = PurchaseItem.objects.filter(invoice=return_order.purchase_invoice, product=prod).first()
                if pur_item:
                    prop = qty / pur_item.quantity
                    discount = (pur_item.discount * prop).quantize(Decimal('0.01'))
                    tax = (pur_item.tax * prop).quantize(Decimal('0.01'))
                    unit_price = pur_item.unit_price
                    item_data['purchase_invoice_item'] = pur_item
            
            item = ReturnItem.objects.create(
                return_order=return_order,
                discount_amount=discount,
                tax_amount=tax,
                unit_price=unit_price,
                **item_data
            )
            total_amount += item.total_price
        
        # Final total
        return_order.total_amount = total_amount
        return_order.save()
        
        return return_order


class ReconciliationEntrySerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    return_number = serializers.CharField(source='return_order.return_number', read_only=True)
    journal_entry_number = serializers.CharField(source='accounting_entry.entry_number', read_only=True)
    party_name = serializers.CharField(source='party.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    fixed_by_name = serializers.CharField(source='fixed_by.first_name', read_only=True)
    
    class Meta:
        model = ReconciliationEntry
        fields = [
            'id', 'invoice', 'invoice_number', 'return_order', 'return_number',
            'accounting_entry', 'journal_entry_number', 'party', 'party_name',
            'supplier', 'supplier_name', 'company', 'transaction_type', 'amount',
            'status', 'fixed_by', 'fixed_by_name', 'fixed_at', 'fix_notes',
            'notes', 'created_at', 'updated_at'
        ]