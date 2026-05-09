"""Job Service Tests"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from jobs.models import BackgroundJob, JobState, JobType
from jobs.services import JobService, JobRunner
from core.models import Company

User = get_user_model()


class JobServiceTests(TestCase):
    """Test JobService"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_create_job_success(self):
        job = JobService.create_job(
            job_type=JobType.REPORT_GENERATION,
            company_id=str(self.company.id),
            payload={'report_type': 'trial_balance'},
            triggered_by=self.user,
            priority='NORMAL'
        )
        
        self.assertEqual(job.job_type, JobType.REPORT_GENERATION)
        self.assertEqual(job.status, JobState.PENDING)
        self.assertEqual(job.company, self.company)
        self.assertEqual(job.triggered_by, self.user)
    
    def test_create_job_invalid_type(self):
        with self.assertRaises(ValueError) as ctx:
            JobService.create_job(
                job_type='invalid_type',
                company_id=str(self.company.id),
                payload={}
            )
        
        self.assertIn('Unknown job type', str(ctx.exception))
    
    def test_create_job_with_none_company(self):
        # Test with no company (system-wide job)
        job = JobService.create_job(
            job_type=JobType.REPORT_GENERATION,
            company_id=None,
            payload={}
        )
        
        self.assertIsNone(job.company)
        self.assertEqual(job.status, JobState.PENDING)
    
    def test_get_job_status(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={}
        )
        
        status = JobService.get_job_status(job.id)
        
        self.assertEqual(status['id'], job.id)
        self.assertEqual(status['status'], JobState.PENDING)
        self.assertIn('created_at', status)
    
    def test_get_job_status_not_found(self):
        status = JobService.get_job_status(99999)
        self.assertIsNone(status)
    
    def test_cancel_job(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={}
        )
        
        result = JobService.cancel_job(job.id)
        
        self.assertTrue(result)
        job.refresh_from_db()
        self.assertEqual(job.status, JobState.CANCELLED)
    
    def test_cancel_job_already_running(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.RUNNING,
            payload={}
        )
        
        result = JobService.cancel_job(job.id)
        
        self.assertFalse(result)
    
    def test_retry_job(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.FAILED,
            error_message='Test error',
            payload={}
        )
        
        result = JobService.retry_job(job.id)
        
        self.assertTrue(result)
        job.refresh_from_db()
        self.assertEqual(job.status, JobState.PENDING)
        self.assertEqual(job.error_message, '')
    
    def test_retry_job_wrong_status(self):
        job = BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={}
        )
        
        result = JobService.retry_job(job.id)
        
        self.assertFalse(result)


class JobRunnerTests(TestCase):
    """Test JobRunner"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_get_job_stats(self):
        # Create some jobs
        BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.COMPLETED,
            started_at=timezone.now(),
            completed_at=timezone.now(),
            payload={}
        )
        
        BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.FAILED,
            payload={}
        )
        
        BackgroundJob.objects.create(
            job_type=JobType.REPORT_GENERATION,
            company=self.company,
            status=JobState.PENDING,
            payload={}
        )
        
        stats = JobRunner.get_job_stats(str(self.company.id))
        
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['pending'], 1)
    
    def test_get_job_stats_all_companies(self):
        stats = JobRunner.get_job_stats()
        
        self.assertIn('total', stats)
        self.assertIn('completed', stats)
        self.assertIn('failed', stats)


class IdempotencyTests(TestCase):
    """Test idempotency protection"""
    
    def setUp(self):
        self.company = Company.objects.create(name='Test Company', is_active=True)
    
    def test_duplicate_job_skipped(self):
        idempotency_key = 'test-idempotency-key'
        
        # First job
        job1 = JobService.create_job(
            job_type=JobType.CLEANUP_TASK,
            company_id=str(self.company.id),
            payload={'cleanup_type': 'old_sessions'},
            idempotency_key=idempotency_key
        )
        
        # Second job with same key should be skipped
        job2 = JobService.create_job(
            job_type=JobType.CLEANUP_TASK,
            company_id=str(self.company.id),
            payload={'cleanup_type': 'old_sessions'},
            idempotency_key=idempotency_key
        )
        
        self.assertEqual(job1.id, job2.id)


class MultiCompanyTests(TestCase):
    """Test multi-company isolation"""
    
    def setUp(self):
        import uuid
        self.company1 = Company.objects.create(
            name='Company 1', 
            code=f'C1-{uuid.uuid4().hex[:8]}',
            is_active=True
        )
        self.company2 = Company.objects.create(
            name='Company 2', 
            code=f'C2-{uuid.uuid4().hex[:8]}',
            is_active=True
        )
    
    def test_jobs_isolated_by_company(self):
        job1 = JobService.create_job(
            job_type=JobType.REPORT_GENERATION,
            company_id=str(self.company1.id),
            payload={}
        )
        
        job2 = JobService.create_job(
            job_type=JobType.REPORT_GENERATION,
            company_id=str(self.company2.id),
            payload={}
        )
        
        self.assertEqual(job1.company, self.company1)
        self.assertEqual(job2.company, self.company2)
        self.assertNotEqual(job1.company, job2.company)
    
    def test_stats_filtered_by_company(self):
        # Create jobs for company1
        JobService.create_job(
            job_type=JobType.REPORT_GENERATION,
            company_id=str(self.company1.id),
            payload={}
        )
        
        # Create jobs for company2
        JobService.create_job(
            job_type=JobType.REPORT_GENERATION,
            company_id=str(self.company2.id),
            payload={}
        )
        
        stats1 = JobRunner.get_job_stats(str(self.company1.id))
        stats2 = JobRunner.get_job_stats(str(self.company2.id))
        
        self.assertEqual(stats1['total'], 1)
        self.assertEqual(stats2['total'], 1)