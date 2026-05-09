import uuid
from django.db import models


class BaseModel(models.Model):
    """Base model with UUID and timestamps."""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class TimeStampedUUIDModel(BaseModel):
    """TimeStampedUUIDModel - kept for backward compatibility."""
    
    class Meta:
        abstract = True
