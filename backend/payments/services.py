from decimal import Decimal
from datetime import date
from typing import Optional
from django.db import transaction as db_transaction, models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from payments.models import (
    PaymentMethod,
    PaymentAccount,
    FinancialTransaction,
    TransactionSettlement,
    SettlementTransaction,
)
from accounting.services.journal_engine import JournalEngine
from accounting.models import Account


class PaymentEngine:
    """
    Core payment processing engine.
    
    Handles:
    - Receipts (money in)
    - Payments (money out)
    - Transfers (between accounts)
    - Refunds
    - Fee calculation
    - Settlement tracking
    - Journal entry creation
    """

    @staticmethod
    @db_transaction.atomic
    def process_receipt(
        payment_method_code: str,
        destination_account_code: str,
        amount: Decimal,
        description: str,
        currency: str = 'AFN',
        party_type: str = '',
        party_id: Optional[str] = None,
        party_name: str = '',
        invoice_type: str = '',
        invoice_id: Optional[str] = None,
        reference_number: str = '',
        mobile_number: str = '',
        exchange_rate: Decimal = Decimal('1.000000'),
        fee_override: Optional[Decimal] = None,
        hawala_dealer: str = '',
        hawala_token: str = '',
        hawala_origin: str = '',
        hawala_destination: str = '',
        value_date: Optional[date] = None,
        performed_by: str = '',
    ) -> dict:
        """
        Process a receipt (money coming in).
        
        Returns dict with success status and transaction details.
        """
        try:
            payment_method = PaymentMethod.objects.get(code=payment_method_code, is_active=True)
        except PaymentMethod.DoesNotExist:
            return {'success': False, 'errors': [_('Payment method not found or inactive')]}

        try:
            dest_account = PaymentAccount.objects.get(code=destination_account_code, is_active=True)
        except PaymentAccount.DoesNotExist:
            return {'success': False, 'errors': [_('Destination account not found or inactive')]}

        # Calculate fee
        fee = fee_override if fee_override is not None else payment_method.calculate_fee(amount)
        # Round fee to 2 decimal places to match account precision
        fee = fee.quantize(Decimal('0.01'))
        net_amount = amount - fee
        # Round net_amount to 2 decimal places to match account precision
        net_amount = net_amount.quantize(Decimal('0.01'))
        # Round net_amount to 2 decimal places to match account precision
        net_amount = net_amount.quantize(Decimal('0.01'))

        # Create transaction
        txn = FinancialTransaction(
            transaction_type='RECEIPT',
            payment_method=payment_method,
            destination_account=dest_account,
            amount=amount,
            currency=currency,
            fee=fee,
            net_amount=net_amount,
            exchange_rate=exchange_rate,
            description=description,
            reference_number=reference_number,
            party_type=party_type,
            party_id=party_id,
            party_name=party_name,
            invoice_type=invoice_type,
            invoice_id=invoice_id,
            transaction_date=timezone.now().date(),
            value_date=value_date or timezone.now().date(),
            mobile_number=mobile_number,
            mobile_operator=payment_method.provider_name,
            hawala_dealer=hawala_dealer,
            hawala_token=hawala_token,
            hawala_origin=hawala_origin,
            hawala_destination=hawala_destination,
            performed_by=performed_by,
            status='COMPLETED',
        )
        txn.save()

        # Update destination account balance
        dest_account.current_balance += net_amount
        dest_account.save(update_fields=['current_balance', 'updated_at'])

        # Create journal entry
        journal_result = PaymentEngine._create_receipt_journal_entry(txn)
        if journal_result.get('success'):
            txn.journal_entry_id = journal_result.get('entry_id')
            txn.save(update_fields=['journal_entry_id', 'updated_at'])

        return {
            'success': True,
            'transaction_number': txn.transaction_number,
            'amount': str(amount),
            'fee': str(fee),
            'net_amount': str(net_amount),
            'destination_balance': str(dest_account.current_balance),
            'journal_entry': journal_result.get('entry_number'),
        }

    @staticmethod
    @db_transaction.atomic
    def process_payment(
        payment_method_code: str,
        source_account_code: str,
        amount: Decimal,
        description: str,
        currency: str = 'AFN',
        party_type: str = '',
        party_id: Optional[str] = None,
        party_name: str = '',
        invoice_type: str = '',
        invoice_id: Optional[str] = None,
        reference_number: str = '',
        exchange_rate: Decimal = Decimal('1.000000'),
        fee_override: Optional[Decimal] = None,
        hawala_dealer: str = '',
        hawala_token: str = '',
        hawala_origin: str = '',
        hawala_destination: str = '',
        value_date: Optional[date] = None,
        performed_by: str = '',
    ) -> dict:
        """
        Process a payment (money going out).
        
        Returns dict with success status and transaction details.
        """
        try:
            payment_method = PaymentMethod.objects.get(code=payment_method_code, is_active=True)
        except PaymentMethod.DoesNotExist:
            return {'success': False, 'errors': [_('Payment method not found or inactive')]}

        try:
            source_account = PaymentAccount.objects.get(code=source_account_code, is_active=True)
        except PaymentAccount.DoesNotExist:
            return {'success': False, 'errors': [_('Source account not found or inactive')]}

        # Calculate fee
        fee = fee_override if fee_override is not None else payment_method.calculate_fee(amount)
        # Round fee to 2 decimal places to match account precision
        fee = fee.quantize(Decimal('0.01'))
        total_deduction = amount + fee
        # Round total_deduction to 2 decimal places to match account precision
        total_deduction = total_deduction.quantize(Decimal('0.01'))

        # Check sufficient funds
        if not source_account.can_withdraw(total_deduction):
            return {
                'success': False,
                'errors': [_(f'Insufficient funds. Available: {source_account.current_balance}, Required: {total_deduction}')]
            }

        # Create transaction
        txn = FinancialTransaction(
            transaction_type='PAYMENT',
            payment_method=payment_method,
            source_account=source_account,
            amount=amount,
            currency=currency,
            fee=fee,
            net_amount=amount,
            exchange_rate=exchange_rate,
            description=description,
            reference_number=reference_number,
            party_type=party_type,
            party_id=party_id,
            party_name=party_name,
            invoice_type=invoice_type,
            invoice_id=invoice_id,
            transaction_date=timezone.now().date(),
            value_date=value_date or timezone.now().date(),
            hawala_dealer=hawala_dealer,
            hawala_token=hawala_token,
            hawala_origin=hawala_origin,
            hawala_destination=hawala_destination,
            performed_by=performed_by,
            status='COMPLETED',
        )
        txn.save()

        # Update source account balance
        source_account.current_balance -= total_deduction
        source_account.save(update_fields=['current_balance', 'updated_at'])

        # Create journal entry
        journal_result = PaymentEngine._create_payment_journal_entry(txn)
        if journal_result.get('success'):
            txn.journal_entry_id = journal_result.get('entry_id')
            txn.save(update_fields=['journal_entry_id', 'updated_at'])

        return {
            'success': True,
            'transaction_number': txn.transaction_number,
            'amount': str(amount),
            'fee': str(fee),
            'total_deducted': str(total_deduction),
            'source_balance': str(source_account.current_balance),
            'journal_entry': journal_result.get('entry_number'),
        }

    @staticmethod
    @db_transaction.atomic
    def process_transfer(
        source_account_code: str,
        destination_account_code: str,
        amount: Decimal,
        description: str,
        currency: str = 'AFN',
        fee_override: Optional[Decimal] = None,
        reference_number: str = '',
        performed_by: str = '',
    ) -> dict:
        """
        Process a transfer between payment accounts.
        
        Returns dict with success status and transaction details.
        """
        try:
            source_account = PaymentAccount.objects.get(code=source_account_code, is_active=True)
        except PaymentAccount.DoesNotExist:
            return {'success': False, 'errors': [_('Source account not found or inactive')]}

        try:
            dest_account = PaymentAccount.objects.get(code=destination_account_code, is_active=True)
        except PaymentAccount.DoesNotExist:
            return {'success': False, 'errors': [_('Destination account not found or inactive')]}

        if source_account.id == dest_account.id:
            return {'success': False, 'errors': [_('Cannot transfer to the same account')]}

        if not source_account.can_withdraw(amount):
            return {
                'success': False,
                'errors': [_(f'Insufficient funds. Available: {source_account.current_balance}')]
            }

        # Use cash method for fee (internal transfers typically no fee)
        try:
            cash_method = PaymentMethod.objects.get(method_type='CASH', is_default=True)
        except PaymentMethod.DoesNotExist:
            cash_method = PaymentMethod.objects.filter(method_type='CASH').first()
        
        fee = fee_override if fee_override is not None else Decimal('0.00')
        total_deduction = amount + fee

        # Create transaction
        txn = FinancialTransaction(
            transaction_type='TRANSFER',
            payment_method=cash_method,
            source_account=source_account,
            destination_account=dest_account,
            amount=amount,
            currency=currency,
            fee=fee,
            net_amount=amount,
            description=description,
            reference_number=reference_number,
            transaction_date=timezone.now().date(),
            value_date=timezone.now().date(),
            performed_by=performed_by,
            status='COMPLETED',
        )
        txn.save()

        # Update balances
        source_account.current_balance -= total_deduction
        source_account.save(update_fields=['current_balance', 'updated_at'])

        dest_account.current_balance += amount
        dest_account.save(update_fields=['current_balance', 'updated_at'])

        # Create journal entry
        journal_result = PaymentEngine._create_transfer_journal_entry(txn)
        if journal_result.get('success'):
            txn.journal_entry_id = journal_result.get('entry_id')
            txn.save(update_fields=['journal_entry_id', 'updated_at'])

        return {
            'success': True,
            'transaction_number': txn.transaction_number,
            'amount': str(amount),
            'fee': str(fee),
            'source_balance': str(source_account.current_balance),
            'destination_balance': str(dest_account.current_balance),
            'journal_entry': journal_result.get('entry_number'),
        }

    @staticmethod
    @db_transaction.atomic
    def process_refund(
        original_transaction_number: str,
        refund_amount: Decimal,
        description: str,
        performed_by: str = '',
    ) -> dict:
        """
        Process a refund for a previous transaction.
        
        Returns dict with success status.
        """
        try:
            original_txn = FinancialTransaction.objects.get(
                transaction_number=original_transaction_number,
                status='COMPLETED'
            )
        except FinancialTransaction.DoesNotExist:
            return {'success': False, 'errors': [_('Original transaction not found or not completed')]}

        if original_txn.transaction_type == 'RECEIPT':
            # Refund a receipt -> money goes back out
            return PaymentEngine.process_payment(
                payment_method_code=original_txn.payment_method.code,
                source_account_code=original_txn.destination_account.code,
                amount=refund_amount,
                description=description or f"Refund for {original_transaction_number}",
                currency=original_txn.currency,
                party_type=original_txn.party_type,
                party_id=original_txn.party_id,
                party_name=original_txn.party_name,
                reference_number=original_transaction_number,
                performed_by=performed_by,
            )
        else:
            # Refund a payment -> money comes back in
            return PaymentEngine.process_receipt(
                payment_method_code=original_txn.payment_method.code,
                destination_account_code=original_txn.source_account.code,
                amount=refund_amount,
                description=description or f"Refund for {original_transaction_number}",
                currency=original_txn.currency,
                party_type=original_txn.party_type,
                party_id=original_txn.party_id,
                party_name=original_txn.party_name,
                reference_number=original_transaction_number,
                performed_by=performed_by,
            )

    @staticmethod
    @db_transaction.atomic
    def create_settlement(
        settlement_type: str,
        payment_account_code: str,
        start_date: date,
        end_date: date,
        expected_amount: Decimal,
        description: str,
        external_reference: str = '',
        performed_by: str = '',
    ) -> dict:
        """
        Create a settlement batch.
        
        Returns dict with success status and settlement details.
        """
        try:
            payment_account = PaymentAccount.objects.get(
                code=payment_account_code, is_active=True
            )
        except PaymentAccount.DoesNotExist:
            return {'success': False, 'errors': [_('Payment account not found')]}

        # Find all unsettled transactions for this account in the date range
        transactions = FinancialTransaction.objects.filter(
            status='COMPLETED',
            is_settled=False,
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
        ).filter(
            models.Q(source_account=payment_account) | models.Q(destination_account=payment_account)
        )

        settlement = TransactionSettlement(
            settlement_type=settlement_type,
            payment_account=payment_account,
            start_date=start_date,
            end_date=end_date,
            expected_amount=expected_amount,
            description=description,
            external_reference=external_reference,
            performed_by=performed_by,
            status='IN_PROGRESS',
        )
        settlement.save()

        # Link transactions
        total_included = Decimal('0.00')
        for txn in transactions:
            # Determine the amount that applies to this account
            if txn.destination_account_id == payment_account.id:
                included_amount = txn.net_amount
            elif txn.source_account_id == payment_account.id:
                included_amount = -(txn.amount + txn.fee)
            else:
                continue

            SettlementTransaction.objects.create(
                settlement=settlement,
                transaction=txn,
                included_amount=included_amount,
            )
            total_included += included_amount

            # Mark as settled
            txn.is_settled = True
            txn.settlement_reference = settlement.settlement_number
            txn.save(update_fields=['is_settled', 'settlement_reference', 'updated_at'])

        settlement.actual_amount = total_included
        settlement.status = 'COMPLETED' if settlement.difference == 0 else 'DISCREPANCY'
        settlement.completed_at = timezone.now()
        settlement.save()

        return {
            'success': True,
            'settlement_number': settlement.settlement_number,
            'transactions_count': transactions.count(),
            'expected_amount': str(expected_amount),
            'actual_amount': str(total_included),
            'difference': str(settlement.difference),
            'status': settlement.status,
        }

    # ---- Journal Entry Helpers ----

    @staticmethod
    def _create_receipt_journal_entry(txn: FinancialTransaction) -> dict:
        """Create journal entry for a receipt."""
        lines = [
            {
                'account_id': txn.destination_account.accounting_account_id,
                'debit': txn.net_amount,
                'credit': 0,
                'description': f"Receipt {txn.transaction_number} - {txn.description}"
            },
        ]

        if txn.fee > 0:
            # Fee expense
            try:
                fee_account = Account.objects.filter(
                    account_type='EXPENSE',
                    account_category='OPERATING_EXPENSE'
                ).first()
                if fee_account:
                    lines.append({
                        'account_id': fee_account.id,
                        'debit': txn.fee,
                        'credit': 0,
                        'description': f"Transaction fee for {txn.transaction_number}"
                    })
            except Exception:
                pass

        # Credit party
        if txn.party_type == 'CUSTOMER':
            # Credit Accounts Receivable
            try:
                ar_account = Account.objects.get(code='1130', is_active=True)
                lines.append({
                    'account_id': ar_account.id,
                    'debit': 0,
                    'credit': txn.amount,
                    'description': f"AR reduction - {txn.party_name}"
                })
            except Account.DoesNotExist:
                # Fallback to the first asset account if 1130 not found
                ar_account = Account.objects.filter(account_type='ASSET', is_active=True).first()
                if not ar_account:
                    return {'success': False, 'errors': ['Accounts Receivable account not found']}
                lines.append({
                    'account_id': ar_account.id,
                    'debit': 0,
                    'credit': txn.amount,
                    'description': f"AR reduction - {txn.party_name}"
                })
        else:
            # Default to revenue or suspense
            try:
                revenue_account = Account.objects.filter(
                    account_type='REVENUE'
                ).first()
                if revenue_account:
                    lines.append({
                        'account_id': revenue_account.id,
                        'debit': 0,
                        'credit': txn.amount,
                        'description': f"Revenue - {txn.description}"
                    })
            except Exception:
                pass

        if len(lines) < 2:
            return {'success': False, 'errors': ['Cannot create balanced journal entry']}

        return JournalEngine.create_entry(
            entry_type='RECEIPT',
            description=f"Receipt {txn.transaction_number}: {txn.description}",
            lines=lines,
            entry_date=txn.transaction_date,
            reference=txn.reference_number or txn.transaction_number,
            auto_post=True
        )

    @staticmethod
    def _create_payment_journal_entry(txn: FinancialTransaction) -> dict:
        """Create journal entry for a payment."""
        lines = []

        # Debit: expense account (where money is going)
        try:
            expense_account = Account.objects.filter(
                account_type='EXPENSE',
                account_category='OPERATING_EXPENSE'
            ).first()
            if expense_account:
                lines.append({
                    'account_id': expense_account.id,
                    'debit': txn.amount,
                    'credit': 0,
                    'description': f"Payment {txn.transaction_number} - {txn.description}"
                })
            else:
                # Fallback to first expense account if specific category not found
                expense_account = Account.objects.filter(account_type='EXPENSE', is_active=True).first()
                if expense_account:
                    lines.append({
                        'account_id': expense_account.id,
                        'debit': txn.amount,
                        'credit': 0,
                        'description': f"Payment {txn.transaction_number} - {txn.description}"
                    })
                else:
                    return {'success': False, 'errors': ['Expense account not found for payment journal entry']}
        except Exception:
            return {'success': False, 'errors': ['Expense account not found for payment journal entry']}

        if txn.fee > 0:
            try:
                fee_account = Account.objects.filter(
                    account_type='EXPENSE',
                    account_category='OPERATING_EXPENSE'
                ).first()
                if fee_account:
                    lines.append({
                        'account_id': fee_account.id,
                        'debit': txn.fee,
                        'credit': 0,
                        'description': f"Transaction fee for {txn.transaction_number}"
                    })
            except Exception:
                pass

        # Credit: source account (where money is coming from)
        lines.append({
            'account_id': txn.source_account.accounting_account_id,
            'debit': 0,
            'credit': txn.amount + txn.fee,
            'description': f"Payment out - {txn.description}"
        })

        if len(lines) < 2:
            return {'success': False, 'errors': ['Cannot create balanced journal entry']}

        return JournalEngine.create_entry(
            entry_type='PAYMENT',
            description=f"Payment {txn.transaction_number}: {txn.description}",
            lines=lines,
            entry_date=txn.transaction_date,
            reference=txn.reference_number or txn.transaction_number,
            auto_post=True
        )

    @staticmethod
    def _create_transfer_journal_entry(txn: FinancialTransaction) -> dict:
        """Create journal entry for a transfer."""
        lines = [
            {
                'account_id': txn.destination_account.accounting_account_id,
                'debit': txn.amount,
                'credit': 0,
                'description': f"Transfer in from {txn.source_account.name}"
            },
            {
                'account_id': txn.source_account.accounting_account_id,
                'debit': 0,
                'credit': txn.amount + txn.fee,
                'description': f"Transfer out to {txn.destination_account.name}"
            },
        ]

        if txn.fee > 0:
            try:
                fee_account = Account.objects.filter(
                    account_type='EXPENSE',
                    account_category='OPERATING_EXPENSE'
                ).first()
                if fee_account:
                    lines.append({
                        'account_id': fee_account.id,
                        'debit': txn.fee,
                        'credit': 0,
                        'description': f"Transfer fee for {txn.transaction_number}"
                    })
            except Exception:
                pass

        return JournalEngine.create_entry(
            entry_type='TRANSFER',
            description=f"Transfer {txn.transaction_number}: {txn.description}",
            lines=lines,
            entry_date=txn.transaction_date,
            reference=txn.transaction_number,
            auto_post=True
        )

    @staticmethod
    def get_account_transactions(
        account_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """Get all transactions for a payment account."""
        try:
            account = PaymentAccount.objects.get(code=account_code)
        except PaymentAccount.DoesNotExist:
            return {'error': 'Account not found', 'transactions': []}

        filters = models.Q(
            source_account=account
        ) | models.Q(
            destination_account=account
        )

        if start_date:
            filters &= models.Q(transaction_date__gte=start_date)
        if end_date:
            filters &= models.Q(transaction_date__lte=end_date)
        if transaction_type:
            filters &= models.Q(transaction_type=transaction_type)
        if status:
            filters &= models.Q(status=status)

        transactions = FinancialTransaction.objects.filter(filters).order_by(
            '-transaction_date', '-created_at'
        )

        total_in = Decimal('0.00')
        total_out = Decimal('0.00')
        total_fees = Decimal('0.00')

        txn_list = []
        for txn in transactions:
            if txn.destination_account_id == account.id:
                total_in += txn.net_amount
            if txn.source_account_id == account.id:
                total_out += txn.amount + txn.fee
            total_fees += txn.fee

            txn_list.append({
                'transaction_number': txn.transaction_number,
                'transaction_type': txn.transaction_type,
                'status': txn.status,
                'amount': str(txn.amount),
                'fee': str(txn.fee),
                'net_amount': str(txn.net_amount),
                'currency': txn.currency,
                'description': txn.description,
                'reference_number': txn.reference_number,
                'transaction_date': txn.transaction_date.isoformat(),
                'is_settled': txn.is_settled,
            })

        return {
            'account_code': account.code,
            'account_name': account.name,
            'current_balance': str(account.current_balance),
            'transactions': txn_list,
            'summary': {
                'total_in': str(total_in),
                'total_out': str(total_out),
                'total_fees': str(total_fees),
                'transaction_count': len(txn_list),
            },
        }
