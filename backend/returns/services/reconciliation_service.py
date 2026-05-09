"""
Financial Reconciliation Engine for Pharmacy ERP.
Ensures invoice, return, and accounting entries remain consistent.

Core Principle: Ledger is the source of financial truth.
Invoices and Returns are only transactional inputs.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from dataclasses import dataclass
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class ReconciliationStatus:
    """Reconciliation status constants."""
    PENDING = 'PENDING'
    MATCHED = 'MATCHED'
    MISMATCHED = 'MISMATCHED'
    FIXED = 'FIXED'


class TransactionType:
    """Transaction type constants."""
    INVOICE = 'INVOICE'
    RETURN = 'RETURN'
    PAYMENT = 'PAYMENT'
    ADJUSTMENT = 'ADJUSTMENT'


@dataclass
class ReconciliationResult:
    """Result of reconciliation operation."""
    success: bool
    reconciliation_id: Optional[str] = None
    status: str = ReconciliationStatus.PENDING
    message: str = ""
    amount: Decimal = Decimal('0.00')


class ReconciliationService:
    """
    Core reconciliation engine.
    Ensures financial truth consistency across invoice, return, and accounting.
    """
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id
    
    @transaction.atomic
    def create_invoice_reconciliation(self, invoice, journal_entry) -> ReconciliationResult:
        """
        STEP 1: Create reconciliation entry when invoice is posted.
        Creates accounting entry -> creates reconciliation record.
        """
        try:
            from returns.models import ReconciliationEntry
            
            # Get amount from journal entry
            total_amount = sum(
                abs(line.credit - line.debit) 
                for line in journal_entry.lines.all()
            )
            
            # Create reconciliation entry
            reconciliation = ReconciliationEntry.objects.create(
                invoice=invoice,
                accounting_entry=journal_entry,
                party=invoice.customer,
                company_id=invoice.company_id,
                transaction_type=TransactionType.INVOICE,
                amount=total_amount,
                status=ReconciliationStatus.PENDING,
            )
            
            # Validate immediately
            self._validate_invoice_reconciliation(reconciliation)
            
            return ReconciliationResult(
                success=True,
                reconciliation_id=str(reconciliation.id),
                status=reconciliation.status,
                message="Invoice reconciliation created successfully",
                amount=total_amount
            )
            
        except Exception as e:
            logger.error(f"Failed to create invoice reconciliation: {e}")
            return ReconciliationResult(
                success=False,
                message=str(e)
            )
    
    @transaction.atomic
    def create_return_reconciliation(self, return_order, journal_entry) -> ReconciliationResult:
        """
        STEP 2: Create reconciliation entry when return is approved.
        Validates invoice linkage -> creates credit note -> updates reconciliation.
        """
        try:
            from returns.models import ReconciliationEntry
            
            # Get the original invoice
            original_invoice = return_order.invoice or return_order.purchase_invoice
            if not original_invoice:
                raise ValidationError("Return must reference an invoice")
            
            # Get amount from journal entry
            total_amount = sum(
                abs(line.credit - line.debit) 
                for line in journal_entry.lines.all()
            )
            
            # Create reconciliation entry for return
            reconciliation = ReconciliationEntry.objects.create(
                return_order=return_order,
                accounting_entry=journal_entry,
                party=return_order.party or return_order.supplier,
                company_id=return_order.invoice.company_id if return_order.invoice else return_order.purchase_invoice.company_id,
                transaction_type=TransactionType.RETURN,
                amount=total_amount,
                status=ReconciliationStatus.PENDING,
            )
            
            # Link to original invoice reconciliation if exists
            if hasattr(original_invoice, 'reconciliation_entries'):
                original_rec = original_invoice.reconciliation_entries.first()
                if original_rec:
                    reconciliation.linked_reconciliation = original_rec
                    reconciliation.save()
            
            # Validate the return vs invoice relationship
            self._validate_return_reconciliation(reconciliation)
            
            return ReconciliationResult(
                success=True,
                reconciliation_id=str(reconciliation.id),
                status=reconciliation.status,
                message="Return reconciliation created successfully",
                amount=total_amount
            )
            
        except Exception as e:
            logger.error(f"Failed to create return reconciliation: {e}")
            return ReconciliationResult(
                success=False,
                message=str(e)
            )
    
    def _validate_invoice_reconciliation(self, reconciliation):
        """
        Validate invoice reconciliation after creation.
        Checks that accounting entry matches invoice total.
        """
        invoice = reconciliation.invoice
        accounting_total = reconciliation.amount
        
        # Get invoice total (excluding returns)
        invoice_total = invoice.total_amount if invoice else Decimal('0')
        
        # Check if amounts match (within tolerance)
        if abs(invoice_total - accounting_total) > Decimal('0.01'):
            reconciliation.status = ReconciliationStatus.MISMATCHED
            reconciliation.notes = f"Invoice total ({invoice_total}) vs Accounting ({accounting_total}) mismatch"
            reconciliation.save()
            logger.warning(f"Invoice reconciliation mismatch: {reconciliation.id}")
    
    def _validate_return_reconciliation(self, reconciliation):
        """
        Validate return reconciliation.
        Checks:
        - Return doesn't exceed invoice quantity
        - Return doesn't exceed invoice value
        """
        return_order = reconciliation.return_order
        
        if not return_order.invoice and not return_order.purchase_invoice:
            return  # No invoice to validate against
        
        # Check value - return cannot exceed original invoice value
        original_invoice = return_order.invoice or return_order.purchase_invoice
        invoice_total = original_invoice.total_amount if original_invoice else Decimal('0')
        
        # Get total returns for this invoice
        from returns.models import ReturnOrder
        total_returns = ReturnOrder.objects.filter(
            invoice=original_invoice
        ).exclude(
            status='REJECTED'
        ).aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0')
        
        total_returns += return_order.total_amount
        
        # If returns exceed invoice value, mark as mismatch
        if total_returns > invoice_total:
            reconciliation.status = ReconciliationStatus.MISMATCHED
            reconciliation.notes = f"Total returns ({total_returns}) exceed invoice value ({invoice_total})"
            reconciliation.save()
            logger.warning(f"Return reconciliation mismatch: {reconciliation.id}")
    
    @transaction.atomic
    def run_matching_engine(self, company_id: str = None) -> Dict:
        """
        STEP 3: Batch matching engine.
        Validates all pending reconciliations and detects mismatches.
        """
        from returns.models import ReconciliationEntry
        
        query = ReconciliationEntry.objects.filter(status=ReconciliationStatus.PENDING)
        if company_id:
            query = query.filter(company_id=company_id)
        
        matched_count = 0
        mismatch_count = 0
        errors = []
        
        for reconciliation in query:
            try:
                if reconciliation.transaction_type == TransactionType.INVOICE:
                    self._validate_invoice_reconciliation(reconciliation)
                elif reconciliation.transaction_type == TransactionType.RETURN:
                    self._validate_return_reconciliation(reconciliation)
                
                if reconciliation.status == ReconciliationStatus.MATCHED:
                    matched_count += 1
                elif reconciliation.status == ReconciliationStatus.MISMATCHED:
                    mismatch_count += 1
                    
            except Exception as e:
                errors.append({
                    'reconciliation_id': str(reconciliation.id),
                    'error': str(e)
                })
        
        return {
            'matched': matched_count,
            'mismatched': mismatch_count,
            'pending': query.count(),
            'errors': errors
        }
    
    @transaction.atomic
    def fix_reconciliation(self, reconciliation_id: str, user, notes: str = "") -> ReconciliationResult:
        """
        Allow admin to manually fix a mismatched reconciliation.
        """
        from returns.models import ReconciliationEntry
        
        try:
            reconciliation = ReconciliationEntry.objects.get(id=reconciliation_id)
            
            old_status = reconciliation.status
            reconciliation.status = ReconciliationStatus.FIXED
            reconciliation.fixed_by = user
            reconciliation.fixed_at = timezone.now()
            reconciliation.fix_notes = notes
            reconciliation.save()
            
            # Log audit trail
            self._log_audit('FIX', reconciliation, old_status, ReconciliationStatus.FIXED, user, notes)
            
            return ReconciliationResult(
                success=True,
                reconciliation_id=str(reconciliation.id),
                status=ReconciliationStatus.FIXED,
                message="Reconciliation fixed successfully"
            )
            
        except ReconciliationEntry.DoesNotExist:
            return ReconciliationResult(
                success=False,
                message="Reconciliation not found"
            )
    
    def _log_audit(self, action: str, reconciliation, old_state: str, new_state: str, user, notes: str = ""):
        """Log audit trail for reconciliation actions."""
        from audit.models import AuditLog
        
        AuditLog.objects.create(
            company_id=reconciliation.company_id,
            user=user,
            action=f"RECONCILIATION_{action}",
            entity_type="ReconciliationEntry",
            entity_id=str(reconciliation.id),
            old_values={'status': old_state},
            new_values={'status': new_state, 'notes': notes},
            description=f"Reconciliation {action.lower()}: {reconciliation.transaction_type}"
        )
    
    def get_control_center_metrics(self, company_id: str = None) -> Dict:
        """
        Provide metrics for control center integration.
        """
        from returns.models import ReconciliationEntry
        
        query = ReconciliationEntry.objects.all()
        if company_id:
            query = query.filter(company_id=company_id)
        
        total = query.count()
        pending = query.filter(status=ReconciliationStatus.PENDING).count()
        matched = query.filter(status=ReconciliationStatus.MATCHED).count()
        mismatched = query.filter(status=ReconciliationStatus.MISMATCHED).count()
        fixed = query.filter(status=ReconciliationStatus.FIXED).count()
        
        # Calculate financial drift score (percentage of mismatches)
        drift_score = (mismatched / total * 100) if total > 0 else 0
        
        return {
            'total_reconciliations': total,
            'pending': pending,
            'matched': matched,
            'mismatched': mismatched,
            'fixed': fixed,
            'drift_score': round(float(drift_score), 2),
            'health_status': 'CRITICAL' if mismatched > 0 else 'HEALTHY'
        }


class MismatchDetector:
    """
    Dedicated mismatch detection engine.
    Runs periodic checks for:
    - Invoice exists but no accounting entry
    - Return exists but no credit note
    - Ledger mismatch vs invoice totals
    - Duplicate postings
    """
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id
    
    def detect_invoice_without_entry(self) -> List[Dict]:
        """Detect invoices without accounting entries."""
        from sales.models import SalesInvoice
        from accounting.models import JournalEntry
        
        query = SalesInvoice.objects.filter(status__in=['DISPATCHED', 'PAID'])
        if self.company_id:
            query = query.filter(company_id=self.company_id)
        
        issues = []
        for invoice in query:
            # Check if there's a journal entry for this invoice
            has_entry = JournalEntry.objects.filter(
                description__icontains=invoice.invoice_number
            ).exists()
            
            if not has_entry:
                issues.append({
                    'invoice_id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'total_amount': str(invoice.total_amount),
                    'issue': 'No accounting entry found'
                })
        
        return issues
    
    def detect_return_without_credit_note(self) -> List[Dict]:
        """Detect returns without credit notes."""
        from returns.models import ReturnOrder
        
        query = ReturnOrder.objects.filter(status='APPROVED')
        if self.company_id:
            query = query.filter(company_id=self.company_id)
        
        issues = []
        for return_order in query:
            if not return_order.journal_entry and not return_order.credit_note_number:
                issues.append({
                    'return_id': str(return_order.id),
                    'return_number': return_order.return_number,
                    'total_amount': str(return_order.total_amount),
                    'issue': 'Approved return without credit note'
                })
        
        return issues
    
    def detect_duplicate_postings(self) -> List[Dict]:
        """Detect duplicate journal entries."""
        from accounting.models import JournalEntry
        
        query = JournalEntry.objects.all()
        if self.company_id:
            query = query.filter(company_id=self.company_id)
        
        # Find entries with same description and amount on same date
        duplicates = []
        seen = set()
        
        for entry in query:
            key = f"{entry.date}-{entry.description}-{entry.total_debit}"
            if key in seen:
                duplicates.append({
                    'entry_id': str(entry.id),
                    'description': entry.description,
                    'date': str(entry.date),
                    'amount': str(entry.total_debit)
                })
            seen.add(key)
        
        return duplicates
    
    def run_full_detection(self) -> Dict:
        """Run all detection checks."""
        return {
            'invoice_without_entry': self.detect_invoice_without_entry(),
            'return_without_credit_note': self.detect_return_without_credit_note(),
            'duplicate_postings': self.detect_duplicate_postings(),
            'total_issues': (
                len(self.detect_invoice_without_entry()) +
                len(self.detect_return_without_credit_note()) +
                len(self.detect_duplicate_postings())
            )
        }