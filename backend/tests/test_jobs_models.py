"""Job Model Tests"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from jobs.models import BackgroundJob, ScheduledTask, JobState, JobPriority, JobType, JobAuditLog
from core.models import Company

User = get_user_model()


class JobStateTests(TestCase):
    """Test JobState class"""
    
    def test_job_states(self):
        self.assertEqual(JobState.PENDING, 'PENDING')
        self.assertEqual(JobState.RUNNING, 'RUNNING')
        self.assertEqual(JobState.COMPLETED, 'COMPLETED')
        self.assertEqual(JobState.FAILED, 'FAILED')
        self.assertEqual(JobState.RETRYING, 'RETRYING')
        self.assertEqual(JobState.CANCELLED, 'CANCELLED')
        self.assertEqual(JobState.STUCK, 'STUCK')
    
    def test_final_states(self):
        self.assertIn(JobState.COMPLETED, JobState.FINAL_STATES)
        self.assertIn(JobState.FAILED, JobState.FINAL_STATES)
        self.assertIn(JobState.CANCELLED, JobState.FINAL_STATES)
        self.assertIn(JobState.STUCK, JobState.FINAL_STATES)
        self.assertNotIn(JobState.PENDING, JobState.FINAL_STATES)
        self.assertNotIn(JobState.RUNNING, JobState.FINAL_STATES)


class JobPriorityTests(TestCase):
    """Test JobPriority class"""
    
    def test_priority_order(self):
        self.assertEqual(JobPriority.ORDER[JobPriority.CRITICAL], 0)
        self.assertEqual(JobPriority.ORDER[JobPriority.HIGH], 1)
        self.assertEqual(JobPriority.ORDER[JobPriority.NORMAL], 2)
        self.assertEqual(JobPriority.ORDER[JobPriority.LOW], 3)


class BackgroundJobTests(TestCase):
    """Test BackgroundJob model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_job(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={'report_type': 'trial_balance', 'params': {}}
        )
        self.assertEqual(job.status, JobState.PENDING)
        self.assertEqual(job.job_type, JobType.REPORT_GENERATION)
        self.assertEqual(job.retry_count, 0)
        self.assertEqual(job.max_retries, 3)
    
    def test_job_lifecycle(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={}
        )
        
        # Start job
        job.start()
        self.assertEqual(job.status, JobState.RUNNING)
        self.assertIsNotNone(job.started_at)
        
        # Complete job
        job.complete({'result': 'success'})
        self.assertEqual(job.status, JobState.COMPLETED)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(job.progress_percent, 100)
        self.assertEqual(job.result, {'result': 'success'})
    
    def test_job_fail_and_retry(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            max_retries=3,
            payload={}
        )
        
        job.start()
        job.fail('Test error', 'Traceback')
        
        self.assertEqual(job.status, JobState.RETRYING)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_message, 'Test error')
    
    def test_can_retry(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.FAILED,
            retry_count=0,
            max_retries=3,
            payload={}
        )
        self.assertTrue(job.can_retry())
        
        job.retry_count = 3
        self.assertFalse(job.can_retry())
        
        job.status = JobState.COMPLETED
        self.assertFalse(job.can_retry())
    
    def test_cancel_job(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={}
        )
        
        job.cancel()
        self.assertEqual(job.status, JobState.CANCELLED)
    
    def test_mark_stuck(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.RUNNING,
            started_at=timezone.now() - timedelta(hours=1),
            payload={}
        )
        
        job.mark_stuck()
        self.assertEqual(job.status, JobState.STUCK)
        self.assertIn('exceeded', job.error_message)
    
    def test_get_duration_seconds(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.RUNNING,
            started_at=timezone.now() - timedelta(seconds=60),
            payload={}
        )
        
        duration = job.get_duration_seconds()
        self.assertGreater(duration, 0)


class ScheduledTaskTests(TestCase):
    """Test ScheduledTask model"""
    
    def setUp(self):
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_scheduled_task(self):
        task = ScheduledTask.objects.create(
            name='Daily Report',
            job_type=JobType.REPORT_GENERATION,
            schedule_type='daily',
            run_time='02:00',
            is_active=True,
            max_retries=3
        )
        self.assertEqual(task.name, 'Daily Report')
        self.assertTrue(task.is_active)
    
    def test_calculate_next_run_daily(self):
        task = ScheduledTask.objects.create(
            name='Daily Task',
            job_type=JobType.CLEANUP_TASK,
            schedule_type='daily',
            run_time='03:00',
            is_active=True
        )
        
        task.calculate_next_run()
        
        self.assertIsNotNone(task.next_run)
        self.assertGreaterEqual(task.next_run, timezone.now())
    
    def test_calculate_next_run_weekly(self):
        task = ScheduledTask.objects.create(
            name='Weekly Task',
            job_type=JobType.CLEANUP_TASK,
            schedule_type='weekly',
            run_time='02:00',
            day_of_week=0,  # Monday
            is_active=True
        )
        
        task.calculate_next_run()
        
        self.assertIsNotNone(task.next_run)
        self.assertGreaterEqual(task.next_run, timezone.now())
    
    def test_calculate_next_run_monthly(self):
        task = ScheduledTask.objects.create(
            name='Monthly Task',
            job_type=JobType.CLEANUP_TASK,
            schedule_type='monthly',
            run_time='02:00',
            day_of_month=1,
            is_active=True
        )
        
        task.calculate_next_run()
        
        self.assertIsNotNone(task.next_run)
        self.assertGreaterEqual(task.next_run, timezone.now())


class JobAuditLogTests(TestCase):
    """Test JobAuditLog model"""
    
    def setUp(self):
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_audit_log(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={}
        )
        
        log = JobAuditLog.objects.create(
            job=job,
            action='STARTED',
            details={'payload': {}},
            duration_seconds=Decimal('0.5')
        )
        
        self.assertEqual(log.action, 'STARTED')
        self.assertEqual(log.job, job)