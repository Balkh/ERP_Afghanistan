"""
Job Signals
Auto-creation and management of background jobs.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save)
def register_jobs_on_app_ready(sender, **kwargs):
    """Register job handlers on app ready"""
    # This is handled by apps.py ready() method
    pass