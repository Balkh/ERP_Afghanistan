"""Credit Policy Engine — Central Credit Enforcement.

Single enforcement hook used by ALL invoice creation entry points.
Credit rules cannot be bypassed via API, admin, or direct model save.

Usage:
    result = CreditPolicyEngine.check_customer_invoice(customer, total_amount)
    if not result.allowed:
        raise ValidationError(result.reason)
"""
from decimal import Decimal
from typing import NamedTuple, Optional


class CreditCheckResult(NamedTuple):
    """Result of a credit policy check."""
    allowed: bool
    reason: str
    requires_override: bool
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


class CreditPolicyEngine:
    """Central credit enforcement engine.
    
    Single enforcement hook for all invoice creation entry points.
    No bypass possible — every path must check through this service.
    """

    # Risk threshold: warn when utilization exceeds 80%
    WARNING_THRESHOLD = Decimal('0.8')
    # Hard limit: block at 100% utilization
    HARD_LIMIT = Decimal('1.0')

    @staticmethod
    def check_customer_invoice(
        customer,
        total_amount: Decimal,
        user=None,
    ) -> CreditCheckResult:
        """Check if a customer can create an invoice of the given amount.
        
        Checks:
        1. Customer is not BLOCKED
        2. Invoice doesn't exceed available credit (unless overridden)
        
        Returns:
            CreditCheckResult with allowed flag, reason, override requirement, and risk level.
        """
        from core.services.financial_audit import FinancialAuditService
        from core.services.financial_truth_engine import FinancialTruthEngine

        # 1. Hard block: customer status is BLOCKED
        if customer.status == 'BLOCKED':
            FinancialAuditService.log_credit_block(
                customer_id=str(customer.pk),
                customer_name=customer.name,
                credit_limit=customer.credit_limit,
                current_balance=customer.balance,
                invoice_amount=total_amount,
                user=user,
            )
            return CreditCheckResult(
                allowed=False,
                reason=f'Customer {customer.name} is blocked from new sales.',
                requires_override=False,
                risk_level='CRITICAL',
            )

        # No credit limit set — no enforcement needed
        if not customer.credit_limit or customer.credit_limit <= 0:
            return CreditCheckResult(
                allowed=True,
                reason='',
                requires_override=False,
                risk_level='LOW',
            )

        # 2. Derive balance from transactions (not stored balance)
        derived_balance = FinancialTruthEngine.get_customer_balance(customer)
        projected_balance = derived_balance + total_amount
        utilization = derived_balance / customer.credit_limit

        # Check hard limit
        if projected_balance > customer.credit_limit:
            return CreditCheckResult(
                allowed=False,
                reason=(
                    f'Credit limit would be exceeded. '
                    f'Limit: {customer.credit_limit}, '
                    f'Current balance: {derived_balance}, '
                    f'Invoice amount: {total_amount}. '
                    f'Use request_credit_override=true to submit for approval.'
                ),
                requires_override=True,
                risk_level='HIGH',
            )

        # Determine risk level based on utilization
        if utilization >= CreditPolicyEngine.HARD_LIMIT:
            risk_level = 'CRITICAL'
        elif utilization >= CreditPolicyEngine.WARNING_THRESHOLD:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return CreditCheckResult(
            allowed=True,
            reason='',
            requires_override=False,
            risk_level=risk_level,
        )

    @staticmethod
    def check_supplier_purchase(
        supplier,
        total_amount: Decimal,
        user=None,
    ) -> CreditCheckResult:
        """Check if a supplier can receive a purchase invoice.
        
        Mirrors customer credit enforcement for supplier parity.
        Checks:
        1. Supplier is not BLOCKED
        2. Purchase doesn't exceed available credit (if credit limit set)
        """
        from core.services.financial_audit import FinancialAuditService
        from core.services.financial_truth_engine import FinancialTruthEngine

        # 1. Hard block: supplier status is BLOCKED
        if supplier.status == 'BLOCKED':
            FinancialAuditService.log_credit_block(
                customer_id=str(supplier.pk),
                customer_name=supplier.name,
                credit_limit=supplier.credit_limit,
                current_balance=supplier.balance,
                invoice_amount=total_amount,
                user=user,
            )
            return CreditCheckResult(
                allowed=False,
                reason=f'Supplier {supplier.name} is blocked.',
                requires_override=False,
                risk_level='CRITICAL',
            )

        # No credit limit set — no enforcement needed
        if not supplier.credit_limit or supplier.credit_limit <= 0:
            return CreditCheckResult(
                allowed=True,
                reason='',
                requires_override=False,
                risk_level='LOW',
            )

        # 2. Derive balance from transactions
        derived_balance = FinancialTruthEngine.get_supplier_balance(supplier)
        projected_balance = derived_balance + total_amount
        utilization = derived_balance / supplier.credit_limit

        if projected_balance > supplier.credit_limit:
            return CreditCheckResult(
                allowed=False,
                reason=(
                    f'Supplier credit limit would be exceeded. '
                    f'Limit: {supplier.credit_limit}, '
                    f'Current balance: {derived_balance}, '
                    f'Purchase amount: {total_amount}.'
                ),
                requires_override=True,
                risk_level='HIGH',
            )

        return CreditCheckResult(
            allowed=True,
            reason='',
            requires_override=False,
            risk_level='LOW' if utilization < CreditPolicyEngine.WARNING_THRESHOLD else 'MEDIUM',
        )

    @staticmethod
    def handle_credit_override(
        customer,
        invoice,
        total_amount: Decimal,
        user=None,
    ):
        """Create a credit approval request for manager override.
        
        Called when an invoice exceeds credit limit but the user
        has requested an override. Creates a CreditApprovalRequest
        for manager approval.
        """
        from sales.models import CreditApprovalRequest
        from core.services.financial_audit import FinancialAuditService

        CreditApprovalRequest.objects.create(
            invoice=invoice,
            customer=customer,
            requested_amount=total_amount,
            current_balance=customer.balance,
            credit_limit=customer.credit_limit,
            requested_by=user,
        )

        FinancialAuditService.log_credit_override(
            customer_id=str(customer.pk),
            customer_name=customer.name,
            credit_limit=customer.credit_limit,
            current_balance=customer.balance,
            invoice_amount=total_amount,
            user=user,
        )
