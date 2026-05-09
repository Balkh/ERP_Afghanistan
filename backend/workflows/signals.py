"""
Workflow Signal Handlers
Auto-create workflows for supported entities.
"""
from decimal import Decimal
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from workflows.models import WorkflowInstance, WorkflowState
from workflows.services import WorkflowService


ENTITY_TYPE_MAP = {
    'sales.SalesInvoice': 'SALES_INVOICE',
    'purchases.PurchaseInvoice': 'PURCHASE_INVOICE',
    'returns.ReturnOrder': 'RETURN_ORDER',
    'accounting.JournalEntry': 'JOURNAL_ENTRY',
}


@receiver(post_save)
def create_workflow_for_entity(sender, instance, created, **kwargs):
    """Auto-create workflow instance when supported entity is created."""
    
    # Skip if not a supported model
    model_path = f"{sender._meta.app_label}.{sender._meta.model_name}"
    if model_path not in ENTITY_TYPE_MAP:
        return
    
    entity_type = ENTITY_TYPE_MAP[model_path]
    
    # Check if workflow already exists
    existing = WorkflowInstance.objects.filter(
        content_type=entity_type,
        object_id=instance.id,
        is_active=True
    ).first()
    
    if existing:
        return
    
    # Get company from instance
    company_id = None
    if hasattr(instance, 'company_id'):
        company_id = instance.company_id
    
    # Get title/reference
    if hasattr(instance, 'invoice_number'):
        ref = instance.invoice_number
        title = f"Sales Invoice {instance.invoice_number}"
    elif hasattr(instance, 'reference_number'):
        ref = instance.reference_number
        title = f"Purchase Invoice {instance.reference_number}"
    else:
        ref = f"{model_path}-{instance.id}"
        title = ref
    
    # Get amount
    amount = Decimal('0')
    if hasattr(instance, 'total_amount'):
        amount = instance.total_amount or Decimal('0')
    
    # Get user
    user = None
    if hasattr(instance, 'created_by'):
        user = instance.created_by
    
    # Create workflow in DRAFT state
    try:
        WorkflowService.create_workflow(
            entity_type=entity_type,
            entity_id=instance.id,
            entity_ref=ref,
            user=user,
            company_id=company_id,
            title=title,
            amount=amount
        )
    except Exception:
        pass  # Skip if creation fails (e.g., validation error)


@receiver(pre_save)
def check_workflow_approval_before_dispatch(sender, instance, **kwargs):
    """Validate workflow approval before dispatching/selling."""
    
    if kwargs.get('raw', False):
        return
    
    model_path = f"{sender._meta.app_label}.{sender._meta.model_name}"
    if model_path not in ENTITY_TYPE_MAP:
        return
    
    # Only check on update
    if not instance.id:
        return
    
    entity_type = ENTITY_TYPE_MAP[model_path]
    
    # For SalesInvoice - check before CONFIRMED/DISPATCHED
    if hasattr(instance, 'status'):
        old_status = None
        try:
            old_instance = sender.objects.get(id=instance.id)
            old_status = old_instance.status
        except sender.DoesNotExist:
            pass
        
        # Check if status is changing to CONFIRMED or DISPATCHED
        new_status = instance.status
        if new_status in ['CONFIRMED', 'DISPATCHED'] and old_status != new_status:
            # Check if workflow allows posting
            if not WorkflowService.can_post(entity_type, instance.id):
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"Cannot {new_status.lower()} invoice. Document must be approved in workflow first."
                )


@receiver(post_save)
def trigger_jobs_on_workflow_state_change(sender, instance, created, **kwargs):
    """Trigger background jobs when workflow state changes"""
    if created:
        return
    
    # Only trigger on workflow instances
    if not isinstance(instance, WorkflowInstance):
        return
    
    # Check if state changed
    if not instance.previous_state or instance.previous_state == instance.current_state:
        return
    
    # Trigger jobs based on new state
    try:
        from jobs.integration import JobWorkflowIntegration
        
        user = instance.triggered_by or instance.created_by
        
        JobWorkflowIntegration.trigger_workflow_jobs(
            workflow=instance,
            new_state=instance.current_state,
            user=user
        )
    except ImportError:
        pass  # Jobs app not available
    except Exception:
        pass  # Don't fail workflow if job triggers fail