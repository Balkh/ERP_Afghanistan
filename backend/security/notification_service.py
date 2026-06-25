"""
Notification service for creating and managing user notifications.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

User = get_user_model()


class NotificationService:
    """Service for creating notifications."""

    @staticmethod
    @transaction.atomic
    def create_notification(
        user,
        notification_type,
        title,
        message,
        severity='INFO',
        product=None,
        warehouse=None,
        batch=None,
        content_type=None,
        object_id=None,
    ):
        """
        Create a notification for a user.
        
        Args:
            user: User instance or ID
            notification_type: Type from Notification.TYPE_CHOICES
            title: Notification title
            message: Notification message
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            product: Optional related Product
            warehouse: Optional related Warehouse
            batch: Optional related Batch
            content_type: Optional ContentType
            object_id: Optional object ID
            
        Returns:
            Created Notification instance
        """
        from security.models import Notification
        
        user_obj = user if hasattr(user, 'id') else User.objects.get(id=user)
        
        notification = Notification.objects.create(
            user=user_obj,
            notification_type=notification_type,
            title=title,
            message=message,
            severity=severity,
            product=product,
            warehouse=warehouse,
            batch=batch,
            content_type=content_type,
            object_id=object_id,
        )
        
        return notification

    @staticmethod
    @transaction.atomic
    def notify_low_stock(user, batch, current_qty, threshold):
        """Create low stock notification."""
        # Get warehouse from batch location (stored as ID)
        warehouse = None
        if batch.location:
            try:
                from inventory.models import Warehouse
                warehouse = Warehouse.objects.get(id=batch.location)
            except Warehouse.DoesNotExist:
                pass
        
        return NotificationService.create_notification(
            user=user,
            notification_type='STOCK_LOW',
            title=f'Low Stock Alert: {batch.product.name}',
            message=f'Batch {batch.batch_number} at warehouse has {current_qty} units remaining (threshold: {threshold})',
            severity='WARNING',
            product=batch.product,
            warehouse=warehouse,
            batch=batch,
        )

    @staticmethod
    @transaction.atomic
    def notify_expiring_batch(user, batch, days_until_expiry):
        """Create expiring batch notification."""
        # Get warehouse from batch location
        warehouse = None
        if batch.location:
            try:
                from inventory.models import Warehouse
                warehouse = Warehouse.objects.get(id=batch.location)
            except Warehouse.DoesNotExist:
                pass
        
        severity = 'CRITICAL' if days_until_expiry <= 7 else 'WARNING'
        return NotificationService.create_notification(
            user=user,
            notification_type='STOCK_EXPIRY',
            title=f'Expiring Batch: {batch.product.name}',
            message=f'Batch {batch.batch_number} expires in {days_until_expiry} days',
            severity=severity,
            product=batch.product,
            warehouse=warehouse,
            batch=batch,
        )

    @staticmethod
    @transaction.atomic
    def notify_out_of_stock(user, product, warehouse):
        """Create out of stock notification."""
        return NotificationService.create_notification(
            user=user,
            notification_type='STOCK_OUT',
            title=f'Out of Stock: {product.name}',
            message=f'{product.name} is out of stock at {warehouse.name}',
            severity='ERROR',
            product=product,
            warehouse=warehouse,
        )

    @staticmethod
    @transaction.atomic
    def notify_user_login(user, ip_address=None):
        """Create user login notification."""
        message = f'User {user.username} logged in'
        if ip_address:
            message += f' from {ip_address}'
        return NotificationService.create_notification(
            user=user,
            notification_type='ACTIVITY_LOGIN',
            title='User Login',
            message=message,
            severity='INFO',
        )

    @staticmethod
    def get_unread_count(user):
        """Get unread notification count for a user."""
        from security.models import Notification
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def mark_as_read(notification_id, user):
        """Mark a notification as read."""
        from security.models import Notification
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user):
        """Mark all notifications as read for a user."""
        from security.models import Notification
        return Notification.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )


def check_low_stock():
    """Check for low stock and create notifications."""
    from inventory.models import Batch
    from django.conf import settings
    
    # Get low stock threshold from settings (default 10)
    threshold = getattr(settings, 'LOW_STOCK_THRESHOLD', 10)
    default_warehouse = getattr(settings, 'DEFAULT_WAREHOUSE', None)
    
    # Find batches below threshold
    low_batches = Batch.objects.filter(
        remaining_quantity__lte=threshold,
        is_active=True,
        product__is_active=True,
    ).select_related('product')
    
    notifications_created = 0
    
    # Get notification users (users with inventory permissions)
    from security.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # For each low stock batch, notify inventory managers
    for batch in low_batches:
        # Check if we already notified recently
        recent_notification = Notification.objects.filter(
            batch=batch,
            notification_type='STOCK_LOW',
            created_at__gte=timezone.now() - timezone.timedelta(hours=24),
        ).exists()
        
        if not recent_notification:
            # Notify superusers or all users with specific role
            users = User.objects.filter(is_superuser=True)[:5]
            for user in users:
                try:
                    NotificationService.notify_low_stock(
                        user=user,
                        batch=batch,
                        current_qty=batch.remaining_quantity,
                        threshold=threshold,
                    )
                    notifications_created += 1
                except Exception:
                    pass
    
    return notifications_created


def check_expiring_batches():
    """Check for expiring batches and create notifications."""
    from inventory.models import Batch
    from django.utils import timezone
    from datetime import timedelta
    
    # Check batches expiring in 30, 14, 7, and 1 days
    check_days = [30, 14, 7, 1]
    
    notifications_created = 0
    
    from security.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    for days in check_days:
        check_date = timezone.now().date() + timedelta(days=days)
        expiring_batches = Batch.objects.filter(
            expiry_date=check_date,
            is_active=True,
            product__is_active=True,
            remaining_quantity__gt=0,
        ).select_related('product')
        
        for batch in expiring_batches:
            recent_notification = Notification.objects.filter(
                batch=batch,
                notification_type='STOCK_EXPIRY',
                created_at__gte=timezone.now() - timedelta(hours=24),
            ).exists()
            
            if not recent_notification:
                users = User.objects.filter(is_superuser=True)[:5]
                for user in users:
                    try:
                        NotificationService.notify_expiring_batch(
                            user=user,
                            batch=batch,
                            days_until_expiry=days,
                        )
                        notifications_created += 1
                    except Exception:
                        pass
    
    return notifications_created