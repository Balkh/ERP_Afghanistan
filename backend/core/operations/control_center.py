"""
Enterprise Control Center - Real-time ERP Monitoring Dashboard.
Provides centralized operational visibility and system intelligence.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Max, Min
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class ControlCenterAggregator:
    """Aggregate all ERP metrics for real-time dashboard."""

    @staticmethod
    def get_live_health() -> dict:
        """Get live system health metrics."""
        from core.operations.health import HealthMonitor

        return {
            'database': HealthMonitor.check_database(),
            'system': HealthMonitor.check_system(),
            'services': HealthMonitor.check_background_services(),
            'timestamp': timezone.now().isoformat()
        }

    @staticmethod
    def get_financial_dashboard() -> dict:
        """Get financial overview for dashboard."""
        from accounting.models import Account, JournalEntry, JournalEntryLine
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        accounts = Account.objects.filter(is_active=True)
        total_assets = sum(a.total_balance for a in accounts.filter(account_type='ASSET'))
        total_liabilities = sum(a.total_balance for a in accounts.filter(account_type='LIABILITY'))
        total_equity = sum(a.total_balance for a in accounts.filter(account_type='EQUITY'))

        todays_sales = SalesInvoice.objects.filter(
            invoice_date__gte=today_start,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        todays_purchases = PurchaseInvoice.objects.filter(
            invoice_date__gte=today_start,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        pending_invoices = SalesInvoice.objects.filter(status='pending').count()
        pending_bills = PurchaseInvoice.objects.filter(status='pending').count()

        posted_entries = JournalEntry.objects.filter(is_posted=True).count()
        unposted_entries = JournalEntry.objects.filter(is_posted=False).count()

        return {
            'balance_summary': {
                'total_assets': str(total_assets),
                'total_liabilities': str(total_liabilities),
                'total_equity': str(total_equity)
            },
            'today_activity': {
                'sales': str(todays_sales),
                'purchases': str(todays_purchases)
            },
            'pending_counts': {
                'sales_invoices': pending_invoices,
                'purchase_bills': pending_bills
            },
            'journal_status': {
                'posted': posted_entries,
                'unposted': unposted_entries
            }
        }

    @staticmethod
    def get_inventory_dashboard() -> dict:
        """Get inventory overview for dashboard."""
        from inventory.models import Product, Batch, Warehouse, StockMovement
        from django.db.models import Sum

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_products = Product.objects.filter(is_active=True).count()
        total_batches = Batch.objects.count()
        active_warehouses = Warehouse.objects.filter(is_active=True).count()

        out_of_stock = Product.objects.filter(
            is_active=True
        ).exclude(
            batch__remaining_quantity__gt=0
        ).distinct().count()

        expiring_soon = Batch.objects.filter(
            expiry_date__gte=now.date(),
            expiry_date__lte=now.date() + timedelta(days=30),
            remaining_quantity__gt=0
        ).count()

        expired_batches = Batch.objects.filter(
            expiry_date__lt=now.date(),
            remaining_quantity__gt=0
        ).count()

        todays_movements = StockMovement.objects.filter(
            created_at__gte=today_start
        ).count()

        return {
            'overview': {
                'total_products': total_products,
                'total_batches': total_batches,
                'active_warehouses': active_warehouses
            },
            'stock_alerts': {
                'out_of_stock': out_of_stock,
                'low_stock': 0,
                'expiring_soon': expiring_soon,
                'expired': expired_batches
            },
            'activity': {
                'movements_today': todays_movements
            }
        }

    @staticmethod
    def get_operations_dashboard() -> dict:
        """Get operations metrics for dashboard."""
        from core.operations.api_observability import get_metrics
        from core.operations.alerts import AlertManager
        from core.operations.stability import StabilityValidator

        metrics = get_metrics()
        stability = StabilityValidator.get_stability_score()

        recent_alerts = AlertManager.get_recent_alerts(hours=24, limit=10)

        error_count = len(metrics.get_bad_requests(hours=1))
        slow_count = len(metrics.get_slow_requests(hours=1))

        return {
            'api_health': {
                'errors_last_hour': error_count,
                'slow_requests_last_hour': slow_count,
                'top_bad_endpoints': metrics.get_top_bad_endpoints(hours=1),
                'top_slow_endpoints': metrics.get_top_slow_endpoints(hours=1)
            },
            'alerts': {
                'recent_count': len(recent_alerts),
                'recent': [a.to_dict() for a in recent_alerts[:5]]
            },
            'stability': stability,
            'performance_budget': {
                'status': 'ok',
                'enforcement_active': True
            }
        }

    @staticmethod
    def get_hr_dashboard() -> dict:
        """Get HR overview for dashboard."""
        from hr.models import Employee, Department, Attendance

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        active_employees = Employee.objects.filter(is_active=True).count()
        total_departments = Department.objects.filter(is_active=True).count()

        today_attendance = Attendance.objects.filter(date=today_start.date())
        present_count = today_attendance.filter(status='PRESENT').count()
        absent_count = today_attendance.filter(status='ABSENT').count()
        leave_count = today_attendance.filter(status='LEAVE').count()

        return {
            'overview': {
                'active_employees': active_employees,
                'departments': total_departments
            },
            'today_attendance': {
                'present': present_count,
                'absent': absent_count,
                'on_leave': leave_count,
                'total': present_count + absent_count + leave_count
            }
        }

    @staticmethod
    def get_complete_dashboard() -> dict:
        """Get complete control center dashboard."""
        return {
            'health': ControlCenterAggregator.get_live_health(),
            'financial': ControlCenterAggregator.get_financial_dashboard(),
            'inventory': ControlCenterAggregator.get_inventory_dashboard(),
            'operations': ControlCenterAggregator.get_operations_dashboard(),
            'hr': ControlCenterAggregator.get_hr_dashboard(),
            'generated_at': timezone.now().isoformat()
        }


class QuickStatsProvider:
    """Provide quick statistical summaries."""

    @staticmethod
    def get_kpis() -> dict:
        """Get key performance indicators."""
        from accounting.models import JournalEntry
        from sales.models import SalesInvoice
        from inventory.models import Product

        return {
            'total_products': Product.objects.filter(is_active=True).count(),
            'total_invoices': SalesInvoice.objects.count(),
            'total_journal_entries': JournalEntry.objects.count(),
            'timestamp': timezone.now().isoformat()
        }


class JobsStatsProvider:
    """Provide background jobs statistics for control center."""

    @staticmethod
    def get_job_stats() -> dict:
        """Get background jobs statistics."""
        try:
            from jobs.models import BackgroundJob, JobState, ScheduledTask
            from jobs.services import JobRunner
            from django.utils import timezone
            from datetime import timedelta

            now = timezone.now()
            last_24h = now - timedelta(hours=24)

            # Get overall stats
            stats = JobRunner.get_job_stats()

            # Get recent jobs
            recent_jobs = BackgroundJob.objects.order_by('-created_at')[:10]
            recent_list = [
                {
                    'id': str(j.id),
                    'job_type': j.job_type,
                    'status': j.status,
                    'created_at': j.created_at.isoformat(),
                    'completed_at': j.completed_at.isoformat() if j.completed_at else None,
                    'duration_seconds': j.get_duration_seconds(),
                }
                for j in recent_jobs
            ]

            # Get scheduled tasks
            scheduled_tasks = ScheduledTask.objects.filter(is_active=True)[:10]
            scheduled_list = [
                {
                    'name': t.name,
                    'job_type': t.job_type,
                    'schedule_type': t.schedule_type,
                    'run_time': t.run_time,
                    'next_run': t.next_run.isoformat() if t.next_run else None,
                    'last_run': t.last_run.isoformat() if t.last_run else None,
                }
                for t in scheduled_tasks
            ]

            # Get stuck jobs
            stuck_jobs = BackgroundJob.objects.filter(status=JobState.STUCK)[:5]
            stuck_list = [
                {
                    'id': str(j.id),
                    'job_type': j.job_type,
                    'started_at': j.started_at.isoformat() if j.started_at else None,
                    'error_message': j.error_message[:100],
                }
                for j in stuck_jobs
            ]

            return {
                'summary': stats,
                'recent_jobs': recent_list,
                'scheduled_tasks': scheduled_list,
                'stuck_jobs': stuck_list,
                'timestamp': now.isoformat()
            }
        except ImportError:
            return {'error': 'Jobs module not available', 'timestamp': timezone.now().isoformat()}
        except Exception as e:
            return {'error': str(e), 'timestamp': timezone.now().isoformat()}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def control_center(request):
    """Get complete enterprise control center dashboard."""
    return Response(ControlCenterAggregator.get_complete_dashboard())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quick_stats(request):
    """Get quick KPI stats."""
    return Response(QuickStatsProvider.get_kpis())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def health_live(request):
    """Get live health metrics."""
    return Response(ControlCenterAggregator.get_live_health())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_summary(request):
    """Get financial dashboard summary."""
    return Response(ControlCenterAggregator.get_financial_dashboard())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_summary(request):
    """Get inventory dashboard summary."""
    return Response(ControlCenterAggregator.get_inventory_dashboard())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def operations_summary(request):
    """Get operations dashboard summary."""
    return Response(ControlCenterAggregator.get_operations_dashboard())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hr_summary(request):
    """Get HR dashboard summary."""
    return Response(ControlCenterAggregator.get_hr_dashboard())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def operational_intelligence(request):
    """Get deterministic operational intelligence (cached)."""
    from core.operations.operational_intelligence import CachedIntelligenceAggregator

    return Response(CachedIntelligenceAggregator.get_all_intelligence())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signal_summary(request):
    """Get signal coordinator summary."""
    from core.operations.signal_coordinator import get_signal_summary

    return Response(get_signal_summary())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_signals(request):
    """Get active signals from coordinator."""
    from core.operations.signal_coordinator import get_active_signals

    category = request.query_params.get('category')
    min_severity = request.query_params.get('min_severity')

    return Response(get_active_signals(category, min_severity))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_signal(request):
    """Register a new signal through coordinator."""
    from core.operations.signal_coordinator import register_intelligence_signal

    signal = request.data
    result = register_intelligence_signal(signal)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def jobs_dashboard(request):
    """Get background jobs dashboard for control center."""
    return Response(JobsStatsProvider.get_job_stats())