"""
Jobs API Views
REST API for background job management.
"""
from rest_framework import viewsets, status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from jobs.models import BackgroundJob, ScheduledTask, JobState
from jobs.services import JobService, JobRunner
from core.api.responses import APIResponse
from core.multitenant.context import TenantContext


class BackgroundJobViewSet(viewsets.ModelViewSet):
    """Background jobs CRUD"""
    queryset = BackgroundJob.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = super().get_queryset()
        company_id = TenantContext.get_company_id()
        if company_id:
            qs = qs.filter(company_id=company_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        # Filter by job type
        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)
        
        return qs.order_by('-priority', '-created_at')[:100]
    
    def create(self, request):
        """Create a new background job"""
        job_type = request.data.get('job_type')
        payload = request.data.get('payload', {})
        priority = request.data.get('priority', 'NORMAL')
        
        if not job_type:
            return Response(APIResponse.error('job_type is required'), status=400)
        
        company_id = TenantContext.get_company_id()
        
        try:
            job = JobService.create_job(
                job_type=job_type,
                company_id=company_id,
                payload=payload,
                triggered_by=request.user,
                priority=priority
            )
            
            # Start execution
            JobRunner.run_job(job.id)
            
            return Response(APIResponse.success(
                data={
                    'job_id': job.id,
                    'status': job.status,
                    'job_type': job.job_type
                },
                message=f"Job {job_type} created and queued"
            ))
            
        except ValueError as e:
            return Response(APIResponse.error(str(e)), status=400)
        except Exception as e:
            return Response(APIResponse.error(f"Failed to create job: {str(e)}"), status=500)


class JobStatusView(generics.GenericAPIView):
    """Get job status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, job_id):
        result = JobService.get_job_status(job_id)
        
        if result is None:
            return Response(APIResponse.error('Job not found'), status=404)
        
        return Response(APIResponse.success(data=result))


class JobActionView(generics.GenericAPIView):
    """Perform job actions (cancel, retry)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, job_id):
        action = request.data.get('action')
        
        if action == 'cancel':
            success = JobService.cancel_job(job_id)
            if success:
                return Response(APIResponse.success(message='Job cancelled'))
            return Response(APIResponse.error('Cannot cancel job'), status=400)
        
        elif action == 'retry':
            success = JobService.retry_job(job_id)
            if success:
                # Start execution
                JobRunner.run_job(job_id)
                return Response(APIResponse.success(message='Job retry queued'))
            return Response(APIResponse.error('Cannot retry job'), status=400)
        
        return Response(APIResponse.error('Invalid action'), status=400)


class JobStatsView(generics.GenericAPIView):
    """Get job statistics for control center"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        company_id = TenantContext.get_company_id()
        stats = JobRunner.get_job_stats(company_id)
        
        return Response(APIResponse.success(data=stats))


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """Scheduled tasks CRUD"""
    queryset = ScheduledTask.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return super().get_queryset().order_by('name')
    
    def perform_create(self, serializer):
        task = serializer.save()
        task.calculate_next_run()
        task.save()


class RunScheduledTasksView(generics.GenericAPIView):
    """Manually trigger scheduled task runner"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        executed = JobScheduler.run_due_tasks()
        
        return Response(APIResponse.success(
            data={'tasks_run': executed},
            message=f"Executed {executed} scheduled tasks"
        ))


# Import JobScheduler for view
from jobs.services import JobScheduler