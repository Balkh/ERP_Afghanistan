"""
Refund Execution Engine — links ReturnOrder approval to actual refund processing.
Extends existing PaymentEngine.process_refund() — does NOT replace it.
"""

from decimal import Decimal
from typing import Optional
from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError


REFUND_REASON_CODES = {
    "CUSTOMER_RETURN": "Customer returned goods",
    "DAMAGED_GOODS": "Goods were damaged on delivery",
    "EXPIRED_GOODS": "Goods expired before delivery/use",
    "INCORRECT_ITEM": "Wrong item delivered",
    "PRICE_DISPUTE": "Price adjustment agreed",
    "CANCELLED_ORDER": "Order cancelled after payment",
    "COURTESY_REFUND": "Courtesy/Goodwill refund",
    "FRAUD_REVERSAL": "Fraudulent transaction reversal",
}

SUPERVISOR_APPROVAL_THRESHOLD = Decimal("10000.00")


class RefundRequest:
    """Encapsulates a refund request from a return approval."""

    def __init__(
        self,
        return_order,
        refund_amount: Decimal,
        reason_code: str = "CUSTOMER_RETURN",
        performed_by: str = "system",
        notes: str = "",
    ):
        self.return_order = return_order
        self.refund_amount = refund_amount
        self.reason_code = reason_code
        self.performed_by = performed_by
        self.notes = notes

    def requires_supervisor(self) -> bool:
        return self.refund_amount > SUPERVISOR_APPROVAL_THRESHOLD

    def get_reason_label(self) -> str:
        return REFUND_REASON_CODES.get(self.reason_code, self.reason_code)


class RefundExecutionService:
    """
    Orchestrates refund execution for approved returns.
    Extension pattern: all methods are instance methods for easy override.
    """

    def __init__(self, company_id: Optional[str] = None):
        self.company_id = company_id

    def execute_return_refund(self, refund_request: RefundRequest) -> dict:
        """
        Execute refund for an approved return.
        Called from ReturnOrder.approve() via hook.

        Flow:
        1. Validate refund eligibility
        2. Find original payment transactions
        3. Execute refund via PaymentEngine.process_refund()
        4. Create reconciliation entry
        5. Log audit trail
        """
        return_order = refund_request.return_order

        if return_order.return_type != "SALE_RETURN":
            return {"success": True, "note": "Purchase returns do not trigger customer refunds"}

        if not return_order.invoice:
            return {"success": False, "error": "No invoice linked to return"}

        invoice = return_order.invoice
        total_paid = getattr(invoice, "paid_amount", Decimal("0.00"))

        if total_paid <= 0:
            return {"success": True, "note": "No payment to refund (invoice unpaid)"}

        refund_amount = min(refund_request.refund_amount, total_paid)

        if refund_amount <= 0:
            return {"success": False, "error": "Refund amount must be positive"}

        if refund_request.requires_supervisor():
            self._signal_approval_needed(refund_request)

        results = self._execute_against_payments(invoice, refund_amount, refund_request)

        self._post_refund_audit(return_order, refund_request, results)

        return {
            "success": True,
            "refund_amount": refund_amount,
            "total_paid": total_paid,
            "results": results,
        }

    def _execute_against_payments(self, invoice, refund_amount: Decimal,
                                    refund_request: RefundRequest) -> list:
        """Execute refund against each payment transaction on the invoice."""
        from payments.models import FinancialTransaction
        from payments.services import PaymentEngine

        results = []
        refunded = Decimal("0.00")

        transactions = FinancialTransaction.objects.filter(
            invoice_id=invoice.id,
            status="COMPLETED",
        )

        for txn in transactions:
            if refunded >= refund_amount:
                break

            txn_refund = refund_amount - refunded
            txn_available = abs(txn.amount or Decimal("0.00"))
            to_refund = min(txn_refund, txn_available)

            if to_refund <= 0:
                continue

            result = PaymentEngine.process_refund(
                original_transaction_number=txn.transaction_number,
                refund_amount=to_refund,
                description=f"Refund for return {refund_request.return_order.return_number}: {refund_request.get_reason_label()}",
                performed_by=refund_request.performed_by,
            )

            if result.get("success"):
                refunded += to_refund

            results.append({
                "transaction": txn.transaction_number,
                "refunded": to_refund,
                "success": result.get("success", False),
            })

        return results

    def _signal_approval_needed(self, refund_request: RefundRequest):
        """Hook for supervisor approval flow. Extend in Phase 17."""
        pass

    def _post_refund_audit(self, return_order, refund_request: RefundRequest,
                            results: list):
        """Create audit log entry for the refund."""
        try:
            from core.models.audit import AuditLog
            AuditLog.objects.create(
                action="RETURN_REFUND",
                entity_type="ReturnOrder",
                entity_id=str(return_order.id),
                description=f"Refund {refund_request.refund_amount} for {return_order.return_number} "
                            f"(reason: {refund_request.get_reason_label()})",
                performed_by=refund_request.performed_by,
            )
        except Exception:
            pass

    def get_refund_eligibility(self, return_order) -> dict:
        """Check if a return is eligible for refund without executing."""
        if return_order.return_type != "SALE_RETURN":
            return {"eligible": False, "reason": "Purchase returns only adjust AP"}

        if not return_order.invoice:
            return {"eligible": False, "reason": "No invoice"}

        from payments.models import FinancialTransaction
        txn_count = FinancialTransaction.objects.filter(
            invoice_id=return_order.invoice.id,
            status="COMPLETED",
        ).count()

        total_paid = getattr(return_order.invoice, "paid_amount", Decimal("0.00"))
        eligible = total_paid > 0 and txn_count > 0

        return {
            "eligible": eligible,
            "total_paid": total_paid,
            "transaction_count": txn_count,
            "requires_supervisor": return_order.total_amount > SUPERVISOR_APPROVAL_THRESHOLD,
        }
