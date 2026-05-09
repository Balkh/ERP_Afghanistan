"""
Management command to run scheduled tasks.
Usage: python manage.py run_scheduled_tasks
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from jobs.models import BackgroundJob, ScheduledTask, JobState
from jobs.services import JobRunner, JobScheduler
from jobs.integration import ScheduledTaskDefaults


class Command(BaseCommand):
    help = 'Run scheduled background jobs and initialize default tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--init-tasks',
            action='store_true',
            help='Initialize default scheduled tasks',
        )
        parser.add_argument(
            '--company',
            type=str,
            help='Run for specific company ID only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would run without executing',
        )
    
    def handle(self, *args, **options):
        init_tasks = options.get('init_tasks', False)
        company_id = options.get('company')
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.NOTICE('=== Background Jobs Management ==='))
        
        # Initialize default tasks if requested
        if init_tasks:
            self.stdout.write(self.style.NOTICE('\n--- Initializing Default Tasks ---'))
            created = ScheduledTaskDefaults.initialize_system_tasks()
            self.stdout.write(self.style.SUCCESS(f'Created {created} default scheduled tasks'))
        
        # Run due scheduled tasks
        self.stdout.write(self.style.NOTICE('\n--- Running Due Tasks ---'))
        
        if dry_run:
            # Show what would run
            now = timezone.now()
            due_tasks = ScheduledTask.objects.filter(
                is_active=True,
                next_run__lte=now
            )
            self.stdout.write(f'Would run {due_tasks.count()} tasks:')
            for task in due_tasks:
                self.stdout.write(f'  - {task.name} ({task.job_type})')
        else:
            # Run the tasks
            executed = JobScheduler.run_due_tasks()
            self.stdout.write(self.style.SUCCESS(f'Executed {executed} scheduled tasks'))
        
        # Run pending jobs
        self.stdout.write(self.style.NOTICE('\n--- Running Pending Jobs ---'))
        
        if dry_run:
            pending = BackgroundJob.objects.filter(
                status__in=[JobState.PENDING, JobState.RETRYING]
            )
            if company_id:
                pending = pending.filter(company_id=company_id)
            
            self.stdout.write(f'Would run {pending.count()} pending jobs')
        else:
            executed = JobRunner.run_pending_jobs(company_id)
            self.stdout.write(self.style.SUCCESS(f'Executed {executed} pending jobs'))
        
        # Check for stuck jobs
        self.stdout.write(self.style.NOTICE('\n--- Checking Stuck Jobs ---'))
        stuck = JobRunner.detect_stuck_jobs()
        if stuck > 0:
            self.stdout.write(self.style.WARNING(f'Found {stuck} stuck jobs - marked as STUCK'))
        else:
            self.stdout.write('No stuck jobs found')
        
        # Show stats
        self.stdout.write(self.style.NOTICE('\n--- Current Stats ---'))
        stats = JobRunner.get_job_stats(company_id)
        self.stdout.write(f"Total: {stats['total']}")
        self.stdout.write(f"  Pending: {stats['pending']}")
        self.stdout.write(f"  Running: {stats['running']}")
        self.stdout.write(f"  Completed: {stats['completed']}")
        self.stdout.write(f"  Failed: {stats['failed']}")
        self.stdout.write(f"  Stuck: {stats['stuck']}")
        
        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))