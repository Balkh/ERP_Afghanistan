"""
Background task definitions for Pharmacy ERP.
Additive — wraps existing functions; no-op if Celery is unavailable.
Each function can be called directly (synchronous) or via Celery (async).
"""
import logging

logger = logging.getLogger("erp.tasks")

try:
    from config.celery import app as celery_app

    @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
    def generate_report_task(self, report_type: str, params: dict = None):
        """Generate a financial report asynchronously."""
        try:
            from accounting.services.financial_reports import FinancialReportEngine
            if report_type == "trial_balance":
                return FinancialReportEngine.get_trial_balance(**(params or {}))
            elif report_type == "profit_loss":
                return FinancialReportEngine.get_profit_and_loss(**((params or {})))
            elif report_type == "balance_sheet":
                return FinancialReportEngine.get_balance_sheet(**(params or {}))
            elif report_type == "cash_flow":
                return FinancialReportEngine.get_cash_flow_statement(**((params or {})))
            elif report_type == "ar_aging":
                return FinancialReportEngine.get_ar_aging(**(params or {}))
            elif report_type == "ap_aging":
                return FinancialReportEngine.get_ap_aging(**(params or {}))
            elif report_type == "ledger":
                return FinancialReportEngine.get_account_ledger(**((params or {})))
        except Exception as e:
            logger.error("Report generation task failed: %s", e)
            raise self.retry(exc=e)

    @celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
    def export_csv_task(self, report_type: str, data: dict = None):
        """Export a report to CSV asynchronously."""
        try:
            from accounting.services.report_exporter import ReportExporter
            exporter = ReportExporter()
            return exporter.to_csv(report_type, data or {})
        except Exception as e:
            logger.error("CSV export task failed: %s", e)
            raise self.retry(exc=e)

    @celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
    def take_snapshot_task(self, day: int, description: str = ""):
        """Take a C-RUNNER snapshot asynchronously."""
        try:
            from core.runner.snapshot_manager import SnapshotManager
            mgr = SnapshotManager()
            snap = mgr.take_snapshot(day, description)
            return {"day": day, "checksum": getattr(snap, "checksum", None) or snap.get("checksum")}
        except Exception as e:
            logger.error("Snapshot task failed: %s", e)
            raise self.retry(exc=e)

    @celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
    def run_audit_task(self):
        """Run a full audit engine check asynchronously."""
        try:
            from core.audit.engine import AuditEngine
            engine = AuditEngine()
            return engine.run_full_audit()
        except Exception as e:
            logger.error("Audit task failed: %s", e)
            raise self.retry(exc=e)

    @celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
    def rotate_backups_task(self):
        """Run backup rotation policy asynchronously."""
        try:
            from backup.backup_system import BackupManager
            mgr = BackupManager()
            mgr.cleanup_old_backups()
            return {"rotated": True}
        except Exception as e:
            logger.error("Backup rotation task failed: %s", e)
            raise self.retry(exc=e)

    tasks_registered = True
except Exception:
    tasks_registered = False
