"""Mixin providing workflow status loading and action performing for invoice screens.

Extracted from SalesInvoiceScreen and PurchaseInvoiceScreen — both had
nearly identical ``load_workflow_status`` and ``perform_workflow_action``
methods differing only in the invoice-type string.
"""

from ui.constants import (
    COLOR_TEXT_MUTED, COLOR_WARNING, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_INFO, SPACING_SM,
)
from ui.components.dialogs import AlertDialog


# Shared color map for workflow states → label colors.
_WORKFLOW_COLOR_MAP = {
    'DRAFT': COLOR_TEXT_MUTED,
    'PENDING_APPROVAL': COLOR_WARNING,
    'APPROVED': COLOR_SUCCESS,
    'REJECTED': COLOR_DANGER,
    'POSTED': COLOR_INFO,
    'CANCELLED': COLOR_TEXT_MUTED,
}


class InvoiceWorkflowMixin:
    """Mixin that adds ``load_workflow_status`` and ``perform_workflow_action``.

    Subclasses **must** define:
      - ``self.api_client``          — the API client instance
      - ``self.current_invoice_id``  — int or None
      - ``self.workflow_status_label`` — QLabel
      - ``self.submit_wf_btn``       — EnterpriseButton
      - ``self.approve_wf_btn``      — EnterpriseButton
      - ``self.reject_wf_btn``       — EnterpriseButton
      - ``self.post_wf_btn``         — EnterpriseButton

    Subclasses set ``_invoice_type`` as a class attribute (e.g.
    ``'SALES_INVOICE'`` or ``'PURCHASE_INVOICE'``).
    """

    _invoice_type = ''  # Override in subclass

    def load_workflow_status(self, invoice_id: int):
        """Load workflow status for the current invoice."""
        if not invoice_id:
            return

        try:
            result = self.api_client.get_workflow_status(self._invoice_type, invoice_id)
            if not (result.get('success') and result.get('data')):
                return

            data = result['data']
            if data.get('has_workflow') is False:
                self.workflow_status_label.setText("")
                return

            state = data.get('state', 'DRAFT')
            state_display = data.get('state_display', state)

            color = _WORKFLOW_COLOR_MAP.get(state, COLOR_TEXT_MUTED)
            self.workflow_status_label.setText(f"Workflow: {state_display}")
            self.workflow_status_label.setStyleSheet(
                f"color: {color}; font-weight: bold; padding: {SPACING_SM}px;"
            )

            self.submit_wf_btn.setVisible(data.get('can_submit', False))
            self.approve_wf_btn.setVisible(data.get('can_approve', False))
            self.reject_wf_btn.setVisible(data.get('can_approve', False))
            self.post_wf_btn.setVisible(data.get('can_post', False))
        except Exception as e:
            print(f"Error loading workflow status: {e}")

    def perform_workflow_action(self, action: str):
        """Perform a workflow action on the current invoice."""
        if not self.current_invoice_id:
            AlertDialog.warning("Error", "No invoice selected.", self)
            return

        try:
            status_result = self.api_client.get_workflow_status(
                self._invoice_type, self.current_invoice_id
            )
            if (
                not status_result.get('success')
                or not status_result.get('data', {}).get('has_workflow')
            ):
                AlertDialog.warning("Error", "No workflow found for this invoice.", self)
                return

            workflow_id = status_result['data'].get('id')
            if not workflow_id:
                AlertDialog.warning("Error", "Could not find workflow ID.", self)
                return

            comment = ''
            if action in ['reject']:
                from PySide6.QtWidgets import QInputDialog
                comment, ok = QInputDialog.getText(
                    self, f"{action.title()} Reason",
                    f"Enter reason for {action}:",
                )
                if not ok:
                    return

            result = self.api_client.workflow_action(workflow_id, action, comment)

            if result.get('success'):
                AlertDialog.info("Success", f"Invoice {action}ed successfully.", self)
                self.load_workflow_status(self.current_invoice_id)
            else:
                error = result.get('error', {}).get('message', 'Unknown error')
                AlertDialog.warning("Error", f"Failed to {action}: {error}", self)
        except Exception as e:
            AlertDialog.error("Error", f"Error performing workflow action: {str(e)}", self)
