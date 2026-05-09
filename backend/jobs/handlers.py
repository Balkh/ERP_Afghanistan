"""
Built-in Job Handlers
Implementation for all standard job types.
"""
import logging
import csv
import io
import json
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Sum, Count
from django.contrib.auth import get_user_model

from jobs.models import BackgroundJob, JobState
from jobs.job_registry import BaseJobHandler, JobRegistry

logger = logging.getLogger(__name__)
User = get_user_model()


class ReportGenerationHandler(BaseJobHandler):
    """Handler for report generation jobs"""
    
    @property
    def job_type(self):
        return 'report_generation'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        report_type = payload.get('report_type')
        params = payload.get('params', {})
        
        job.progress_percent = 10
        job.progress_message = f"Generating {report_type} report..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        # Import report service
        from accounting.services.financial_reports import FinancialReportService
        
        job.progress_percent = 50
        job.save(update_fields=['progress_percent'])
        
        # Generate report based on type
        if report_type == 'trial_balance':
            result = FinancialReportService.generate_trial_balance(
                params.get('company_id'),
                params.get('start_date'),
                params.get('end_date')
            )
        elif report_type == 'profit_loss':
            result = FinancialReportService.generate_profit_loss(
                params.get('company_id'),
                params.get('start_date'),
                params.get('end_date')
            )
        elif report_type == 'balance_sheet':
            result = FinancialReportService.generate_balance_sheet(
                params.get('company_id'),
                params.get('end_date')
            )
        else:
            result = {'status': 'completed', 'report_type': report_type}
        
        job.progress_percent = 100
        job.progress_message = "Report generated successfully"
        
        return {
            'report_type': report_type,
            'status': 'completed',
            'generated_at': timezone.now().isoformat(),
            'result': result
        }
    
    def get_idempotency_key(self, payload: Dict[str, Any]) -> str:
        return f"report:{payload.get('report_type')}:{payload.get('company_id')}:{payload.get('start_date')}"


class ExportGenerationHandler(BaseJobHandler):
    """Handler for export generation jobs"""
    
    @property
    def job_type(self):
        return 'export_generation'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        export_type = payload.get('export_type')
        filters = payload.get('filters', {})
        
        job.progress_percent = 20
        job.progress_message = f"Preparing {export_type} export..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        # Generate export based on type
        if export_type == 'sales_invoices':
            from sales.models import SalesInvoice
            qs = SalesInvoice.objects.filter(
                company_id=job.company_id,
                **filters
            )[:10000]
            data = list(qs.values('invoice_number', 'total_amount', 'status'))
        
        elif export_type == 'purchase_invoices':
            from purchases.models import PurchaseInvoice
            qs = PurchaseInvoice.objects.filter(
                company_id=job.company_id,
                **filters
            )[:10000]
            data = list(qs.values('invoice_number', 'total_amount', 'status'))
        
        elif export_type == 'inventory':
            from inventory.models import Product
            qs = Product.objects.filter(
                company_id=job.company_id,
                **filters
            )[:10000]
            data = list(qs.values('name', 'sku', 'quantity'))
        
        else:
            data = []
        
        job.progress_percent = 80
        job.save(update_fields=['progress_percent'])
        
        # Create CSV export
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        export_content = output.getvalue()
        output.close()
        
        # Save result with export content
        result = {
            'export_type': export_type,
            'record_count': len(data),
            'status': 'completed',
            'generated_at': timezone.now().isoformat()
        }
        
        job.progress_percent = 100
        job.progress_message = f"Exported {len(data)} records"
        
        return result
    
    def get_idempotency_key(self, payload: Dict[str, Any]) -> str:
        return f"export:{payload.get('export_type')}:{job.company_id}:{payload.get('timestamp')}"


class FinancialReconciliationHandler(BaseJobHandler):
    """Handler for financial reconciliation jobs"""
    
    @property
    def job_type(self):
        return 'financial_reconciliation'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        company_id = job.company_id
        
        job.progress_percent = 10
        job.progress_message = "Starting financial reconciliation..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        from accounting.models import JournalEntry
        from payments.models import FinancialTransaction
        
        # Check journal entries balance
        job.progress_percent = 30
        job.save(update_fields=['progress_percent'])
        
        unbalanced = JournalEntry.objects.filter(
            company_id=company_id,
            isPosted=True
        ).annotate(
            total_debit=Sum('lines__debit'),
            total_credit=Sum('lines__credit')
        ).filter(total_debit__gt=0).exclude(
            total_debit=models.F('total_credit')
        ).count()
        
        job.progress_percent = 60
        job.save(update_fields=['progress_percent'])
        
        # Check pending transactions
        pending_transactions = FinancialTransaction.objects.filter(
            company_id=company_id,
            status='PENDING'
        ).count()
        
        job.progress_percent = 100
        job.progress_message = "Reconciliation complete"
        
        return {
            'status': 'completed',
            'unbalanced_entries': unbalanced,
            'pending_transactions': pending_transactions,
            'reconciled_at': timezone.now().isoformat()
        }
    
    def get_idempotency_key(self, payload: Dict[str, Any]) -> str:
        from django.utils import timezone
        date = payload.get('date', timezone.now().date())
        return f"reconciliation:{job.company_id}:{date}"


class AnomalyScanHandler(BaseJobHandler):
    """Handler for anomaly detection scans"""
    
    @property
    def job_type(self):
        return 'anomaly_scan'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        company_id = job.company_id
        
        job.progress_percent = 10
        job.progress_message = "Running anomaly detection..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        # Use operational intelligence
        try:
            from core.operations.operational_intelligence import RuleBasedAnomalyDetector
            
            detector = RuleBasedAnomalyDetector()
            anomalies = detector.detect_all(company_id)
            
            job.progress_percent = 50
            job.save(update_fields=['progress_percent'])
            
            # Store results
            result = {
                'status': 'completed',
                'anomaly_count': len(anomalies),
                'anomalies': anomalies[:100],  # Limit to 100
                'scanned_at': timezone.now().isoformat()
            }
            
            job.progress_percent = 100
            job.progress_message = f"Found {len(anomalies)} anomalies"
            
            return result
            
        except ImportError:
            return {
                'status': 'completed',
                'anomaly_count': 0,
                'message': 'Anomaly detector not available',
                'scanned_at': timezone.now().isoformat()
            }


class InventoryExpiryScanHandler(BaseJobHandler):
    """Handler for inventory expiry scanning"""
    
    @property
    def job_type(self):
        return 'inventory_expiry_scan'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        company_id = job.company_id
        days_warning = payload.get('days_warning', 30)
        
        job.progress_percent = 10
        job.progress_message = "Scanning for expiring inventory..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        from inventory.models import Batch
        from datetime import date
        
        warning_date = date.today() + timedelta(days=days_warning)
        
        expiring = Batch.objects.filter(
            company_id=company_id,
            expiry_date__lte=warning_date,
            expiry_date__gte=date.today(),
            remaining_quantity__gt=0
        ).select_related('product').order_by('expiry_date')[:500]
        
        job.progress_percent = 60
        job.save(update_fields=['progress_percent'])
        
        # Group by urgency
        soon = []
        critical = []
        
        for batch in expiring:
            days_left = (batch.expiry_date - date.today()).days
            item = {
                'product_name': batch.product.name,
                'batch_number': batch.batch_number,
                'expiry_date': batch.expiry_date.isoformat(),
                'days_left': days_left,
                'quantity': str(batch.remaining_quantity)
            }
            if days_left <= 7:
                critical.append(item)
            else:
                soon.append(item)
        
        job.progress_percent = 100
        job.progress_message = f"Found {len(expiring)} expiring items"
        
        return {
            'status': 'completed',
            'total_expiring': len(expiring),
            'critical_count': len(critical),
            'warning_count': len(soon),
            'critical_items': critical[:50],
            'warning_items': soon[:50],
            'scanned_at': timezone.now().isoformat()
        }


class NotificationDispatchHandler(BaseJobHandler):
    """Handler for batch notification dispatch"""
    
    @property
    def job_type(self):
        return 'notification_dispatch'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        notification_type = payload.get('notification_type')
        user_ids = payload.get('user_ids', [])
        
        job.progress_percent = 20
        job.progress_message = f"Sending {notification_type} notifications..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        from security.notification_service import NotificationService
        
        sent_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                NotificationService.create_notification(
                    user=user,
                    notification_type=notification_type,
                    title=payload.get('title', 'Notification'),
                    message=payload.get('message', ''),
                    severity=payload.get('severity', 'INFO')
                )
                sent_count += 1
            except Exception:
                failed_count += 1
            
            # Update progress every 10 notifications
            if (sent_count + failed_count) % 10 == 0:
                job.progress_percent = min(80, 20 + (sent_count + failed_count) * 60 // len(user_ids))
                job.save(update_fields=['progress_percent'])
        
        job.progress_percent = 100
        job.progress_message = f"Sent {sent_count} notifications"
        
        return {
            'status': 'completed',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'dispatched_at': timezone.now().isoformat()
        }


class CleanupTaskHandler(BaseJobHandler):
    """Handler for cleanup tasks"""
    
    @property
    def job_type(self):
        return 'cleanup_task'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        cleanup_type = payload.get('cleanup_type')
        
        job.progress_percent = 10
        job.progress_message = f"Running cleanup: {cleanup_type}..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        cleaned_count = 0
        
        if cleanup_type == 'old_sessions':
            from django.contrib.sessions.models import Session
            cutoff = timezone.now() - timedelta(days=7)
            cleaned_count = Session.objects.filter(expire_date__lt=cutoff).count()
            Session.objects.filter(expire_date__lt=cutoff).delete()
        
        elif cleanup_type == 'old_notifications':
            from security.models import Notification
            cutoff = timezone.now() - timedelta(days=30)
            cleaned_count = Notification.objects.filter(
                company_id=job.company_id,
                created_at__lt=cutoff,
                is_read=True
            ).count()
            Notification.objects.filter(
                company_id=job.company_id,
                created_at__lt=cutoff,
                is_read=True
            ).delete()
        
        elif cleanup_type == 'old_exports':
            # Clean old completed jobs
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=7)
            cleaned_count = BackgroundJob.objects.filter(
                company_id=job.company_id,
                status=JobState.COMPLETED,
                created_at__lt=cutoff
            ).update(is_active=False)
        
        job.progress_percent = 100
        job.progress_message = f"Cleaned {cleaned_count} items"
        
        return {
            'status': 'completed',
            'cleanup_type': cleanup_type,
            'cleaned_count': cleaned_count,
            'cleaned_at': timezone.now().isoformat()
        }


class OverdueScanHandler(BaseJobHandler):
    """Handler for overdue scan tasks"""
    
    @property
    def job_type(self):
        return 'overdue_scan'
    
    def execute(self, job: BackgroundJob, payload: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import date
        
        job.progress_percent = 10
        job.progress_message = "Scanning for overdue items..."
        job.save(update_fields=['progress_percent', 'progress_message'])
        
        company_id = job.company_id
        today = date.today()
        
        # Scan overdue sales invoices
        from sales.models import SalesInvoice
        from security.notification_service import NotificationService
        
        overdue_sales = SalesInvoice.objects.filter(
            company_id=company_id,
            due_date__lt=today,
            payment_status__in=['UNPAID', 'PARTIAL']
        )
        
        # Create notifications for overdue sales
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_users = User.objects.filter(company_id=company_id, is_staff=True)
        
        for inv in overdue_sales:
            for user in admin_users:
                NotificationService.create_notification(
                    user=user,
                    notification_type='FINANCE_ALERT',
                    title=f"Overdue Invoice: {inv.invoice_number}",
                    message=f"Invoice {inv.invoice_number} is overdue since {inv.due_date}. Total: {inv.total_amount}",
                    severity='WARNING',
                    content_type=None,
                    object_id=str(inv.id)
                )
        
        job.progress_percent = 40
        job.save(update_fields=['progress_percent'])
        
        # Scan overdue purchase invoices
        from purchases.models import PurchaseInvoice
        overdue_purchases = PurchaseInvoice.objects.filter(
            company_id=company_id,
            due_date__lt=today,
            payment_status__in=['UNPAID', 'PARTIAL']
        )
        
        for inv in overdue_purchases:
            for user in admin_users:
                NotificationService.create_notification(
                    user=user,
                    notification_type='FINANCE_ALERT',
                    title=f"Overdue Payment: {inv.invoice_number}",
                    message=f"Purchase {inv.invoice_number} is overdue since {inv.due_date}. Total: {inv.total_amount}",
                    severity='WARNING',
                    content_type=None,
                    object_id=str(inv.id)
                )
        
        job.progress_percent = 70
        job.save(update_fields=['progress_percent'])
        
        # Scan overdue approvals
        from workflows.models import ApprovalRequest
        from django.utils import timezone
        overdue_approvals = ApprovalRequest.objects.filter(
            company_id=company_id,
            status='PENDING',
            due_date__lt=timezone.now()
        ).count()
        
        job.progress_percent = 100
        job.progress_message = "Overdue scan complete"
        
        return {
            'status': 'completed',
            'overdue_sales_count': len(list(overdue_sales)),
            'overdue_purchases_count': len(list(overdue_purchases)),
            'overdue_approvals_count': overdue_approvals,
            'scanned_at': timezone.now().isoformat()
        }