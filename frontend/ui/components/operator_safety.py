"""
Enterprise Operator Safety Layer (Phase D.3).
Production-grade safety mechanisms for ERP operator protection.

No ML/AI — all deterministic, rule-based, low-overhead safety guards.
"""

from PySide6.QtWidgets import QWidget, QDialog
from ui.components.dialogs import AlertDialog, ConfirmDialog
from PySide6.QtCore import Qt, QTimer, Signal
from typing import Optional, Callable, Dict, Any, List
import time
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. DESTRUCTIVE ACTION SAFETY
# ═══════════════════════════════════════════════════════════════

class DestructiveActionGuard:
    """
    Confirmation guard for destructive operations.
    
    Usage:
        guard = DestructiveActionGuard()
        if guard.confirm_delete(parent, "invoice #123"):
            perform_delete()
    """

    @staticmethod
    def confirm_delete(parent: QWidget, target_desc: str = "this item") -> bool:
        """Confirm deletion with irreversible action warning."""
        return ConfirmDialog.confirm("Confirm Deletion", f"Are you sure you want to delete {target_desc}?\n\n" "This action cannot be undone.", parent)

    @staticmethod
    def confirm_accounting_reversal(
        parent: QWidget, entry_desc: str = "this journal entry"
    ) -> bool:
        """Confirm accounting reversal with financial impact warning."""
        return ConfirmDialog.confirm("Confirm Reversal", f"You are about to reverse {entry_desc}.\n\n" "This will create offsetting journal entries and may affect " "period-end balances. Ensure you have proper authorization.\n\n" "Do you want to proceed?", parent)

    @staticmethod
    def confirm_irreversible(parent: QWidget, title: str, message: str) -> bool:
        """Generic irreversible action confirmation."""
        return ConfirmDialog.confirm(title, message, parent)

    @staticmethod
    def confirm_bulk_action(
        parent: QWidget, action_desc: str, count: int
    ) -> bool:
        """Confirm bulk action affecting multiple items."""
        return ConfirmDialog.confirm("Confirm Bulk Action", "This will affect multiple records. Continue?", parent)


# ═══════════════════════════════════════════════════════════════
# 2. FINANCIAL SAFETY
# ═══════════════════════════════════════════════════════════════

class FinancialSafety:
    """
    Financial transaction safety checks.
    
    Usage:
        safety = FinancialSafety()
        if safety.check_credit_limit(parent, customer_balance, credit_limit):
            proceed_with_sale()
    """

    @staticmethod
    def check_credit_limit(
        parent: QWidget,
        current_balance: float,
        credit_limit: float,
        customer_name: str = ""
    ) -> bool:
        """Warn if customer exceeds credit limit. Returns True to proceed."""
        if credit_limit <= 0:
            return True
        if current_balance >= credit_limit:
            customer_str = f" for {customer_name}" if customer_name else ""
            return ConfirmDialog.confirm("Credit Limit Exceeded", f"Customer{customer_str} has exceeded their credit limit.\n" f"Current balance: {current_balance:.2f}\n" f"Credit limit: {credit_limit:.2f}\n\n" "Do you want to proceed anyway?", parent)
        return True

    @staticmethod
    def check_over_payment(
        parent: QWidget,
        payment_amount: float,
        outstanding: float,
        invoice_ref: str = ""
    ) -> bool:
        """Warn if payment exceeds outstanding amount."""
        if payment_amount <= outstanding:
            return True
        inv = f" for {invoice_ref}" if invoice_ref else ""
        return ConfirmDialog.confirm("Overpayment Warning", "Do you want to proceed with the overpayment?", parent)

    @staticmethod
    def check_negative_stock(
        parent: QWidget,
        product_name: str,
        current_qty: float,
        requested_qty: float
    ) -> bool:
        """Warn if transaction would cause negative stock."""
        if current_qty >= requested_qty:
            return True
        return ConfirmDialog.confirm("Negative Stock Warning", f"Insufficient stock for '{product_name}'.\n" f"Available: {current_qty}\n" f"Requested: {requested_qty}\n\n" "Negative stock will be created. Proceed?", parent)

    @staticmethod
    def check_invalid_journal(
        parent: QWidget,
        debits: float,
        credits: float,
        difference: float
    ) -> bool:
        """Warn if journal entry is unbalanced."""
        if abs(difference) < 0.001:
            return True
        return ConfirmDialog.confirm("Unbalanced Journal Entry", f"This journal entry is not balanced.\n" f"Total Debits: {debits:.2f}\n" f"Total Credits: {credits:.2f}\n" f"Difference: {difference:.2f}\n\n" "Do you want to proceed with an unbalanced entry?", parent)


# ═══════════════════════════════════════════════════════════════
# 3. SESSION SAFETY
# ═══════════════════════════════════════════════════════════════

class SessionSafety(QWidget):
    """
    Session safety monitoring — timeout warnings, stale tab detection.
    
    Usage:
        session = SessionSafety(parent)
        session.start_timeout_warning(warning_minutes=2, timeout_minutes=5)
    """

    session_expired = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._last_activity: float = time.time()
        self._warning_timer: Optional[QTimer] = None
        self._timeout_timer: Optional[QTimer] = None
        self._warning_minutes: int = 0
        self._timeout_minutes: int = 0
        self._warning_shown: bool = False

    def start_timeout_warning(self, warning_minutes: int = 2, timeout_minutes: int = 5):
        """Start session timeout monitoring."""
        self._warning_minutes = warning_minutes
        self._timeout_minutes = timeout_minutes
        self._last_activity = time.time()
        self._warning_shown = False

        self._warning_timer = QTimer(self)
        self._warning_timer.timeout.connect(self._check_warning)
        self._warning_timer.start(10000)

        self._timeout_timer = QTimer(self)
        self._timeout_timer.timeout.connect(self._check_timeout)
        self._timeout_timer.start(30000)

    def stop_timeout_monitoring(self):
        """Stop session timeout monitoring."""
        if self._warning_timer:
            self._warning_timer.stop()
            self._warning_timer = None
        if self._timeout_timer:
            self._timeout_timer.stop()
            self._timeout_timer = None
        self._warning_shown = False

    def record_activity(self):
        """Record user activity to reset timeout timer."""
        self._last_activity = time.time()
        self._warning_shown = False

    def _check_warning(self):
        elapsed = (time.time() - self._last_activity) / 60
        if elapsed >= self._warning_minutes and not self._warning_shown:
            remaining = self._timeout_minutes - elapsed
            if remaining > 0:
                AlertDialog.info("Session Timeout Warning",
                    f"Your session will expire in {remaining:.0f} minute(s) due to inactivity.", self)
                self._warning_shown = True

    def _check_timeout(self):
        elapsed = (time.time() - self._last_activity) / 60
        if elapsed >= self._timeout_minutes:
            AlertDialog.warning("Session Expired",
                "Your session has expired due to inactivity.\nPlease log in again.", self)
            self.session_expired.emit()

    @staticmethod
    def detect_stale_tab(storage_key: str = "pharmacy_erp_tab_id") -> bool:
        """
        Detect if a stale browser tab is being used.
        Returns True if current tab is stale compared to latest registered tab.
        """
        import os
        tab_id_path = os.path.join(
            os.path.expanduser("~"), ".pharmacy_erp", f"{storage_key}.txt"
        )
        import uuid
        current_id = str(uuid.uuid4())[:8]
        try:
            os.makedirs(os.path.dirname(tab_id_path), exist_ok=True)
            if os.path.exists(tab_id_path):
                with open(tab_id_path) as f:
                    stored_id = f.read().strip()
                with open(tab_id_path, "w") as f:
                    f.write(current_id)
                return stored_id != current_id
            else:
                with open(tab_id_path, "w") as f:
                    f.write(current_id)
                return False
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════
# 4. INTERACTION SAFETY
# ═══════════════════════════════════════════════════════════════

class InteractionSafety:
    """
    Operator interaction safety guards — prevents accidental misuse.
    """

    @staticmethod
    def guard_double_click(last_click_time: float, threshold: float = 0.5) -> bool:
        """
        Prevent rapid double-clicks. Returns True if click should proceed.
        
        Usage:
            if InteractionSafety.guard_double_click(self._last_click):
                self._last_click = time.time()
                perform_action()
        """
        now = time.time()
        if now - last_click_time < threshold:
            logger.debug("Double-click prevented")
            return False
        return True

    @staticmethod
    def guard_multi_submit(last_submit_time: float, threshold: float = 1.0) -> bool:
        """Prevent accidental multi-submit within threshold."""
        now = time.time()
        if now - last_submit_time < threshold:
            logger.warning("Multi-submit prevented")
            return False
        return True

    @staticmethod
    def enforce_disabled(widget: QWidget, enabled: bool, reason: str = ""):
        """
        Enforce disabled state on a widget with visual feedback.
        
        Usage:
            InteractionSafety.enforce_disabled(save_btn, can_save)
        """
        widget.setEnabled(enabled)
        if not enabled and reason:
            widget.setToolTip(reason)

    @staticmethod
    def confirm_transaction_lock(
        parent: QWidget,
        lock_holder: str,
        resource: str = "this record"
    ) -> bool:
        """Warn if another user holds a transaction lock on the resource."""
        if not lock_holder:
            return True
        return ConfirmDialog.confirm("Record Locked", f"{resource} is currently being edited by '{lock_holder}'.\n\n" "If you proceed, you may overwrite their changes.\n" "Do you want to continue?", parent)


# ═══════════════════════════════════════════════════════════════
# 5. OPERATOR GUIDANCE
# ═══════════════════════════════════════════════════════════════

class OperatorGuidance:
    """
    Contextual guidance and inline instructions for operators.
    """

    @staticmethod
    def show_workflow_hint(
        parent: QWidget,
        title: str,
        message: str,
        detail: str = ""
    ):
        """Show contextual workflow guidance to the operator."""
        AlertDialog.info(title, message, parent)

    @staticmethod
    def show_recovery_guidance(
        parent: QWidget,
        error_desc: str,
        recovery_steps: List[str]
    ):
        """Show safe recovery guidance after an error."""
        steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(recovery_steps))
        AlertDialog.info("Recovery Guidance", f"An error occurred: {error_desc}\n\nRecommended recovery steps:\n\n{steps}", parent)

    @staticmethod
    def format_validation_explanation(errors: Dict[str, str]) -> str:
        """Format validation errors into readable guidance."""
        lines = ["The following fields need attention:"]
        for field, error in errors.items():
            lines.append(f"  - {field}: {error}")
        lines.append("\nPlease correct these fields before proceeding.")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 6. BULK OPERATION SAFETY
# ═══════════════════════════════════════════════════════════════

class BulkOperationGuard:
    """
    Safety guard for bulk operations — confirmation, progress, undo hints.
    """

    @staticmethod
    def confirm_bulk_delete(
        parent: QWidget,
        count: int,
        item_type: str = "items"
    ) -> bool:
        """Confirm bulk deletion with count."""
        if count == 0:
            return False
        return ConfirmDialog.confirm("Bulk Deletion", f"You are about to delete {count} {item_type} permanently.\n\n" "This action cannot be undone. Continue?", parent)

    @staticmethod
    def confirm_bulk_update(
        parent: QWidget,
        count: int,
        action_desc: str = "update",
        item_type: str = "items"
    ) -> bool:
        """Confirm bulk update operation."""
        if count == 0:
            return False
        return ConfirmDialog.confirm("Bulk Update", f"You are about to {action_desc} {count} {item_type}.\n\n" "This will modify multiple records. Continue?", parent)

    @staticmethod
    def confirm_bulk_status_change(
        parent: QWidget,
        count: int,
        new_status: str,
        item_type: str = "items"
    ) -> bool:
        """Confirm bulk status change (approve, reject, cancel)."""
        return ConfirmDialog.confirm("Bulk Status Change", f"You are about to set status to '{new_status}' for {count} {item_type}.\n\n" "This may trigger journal entries, stock movements, or notifications.\n" "Continue?", parent)
