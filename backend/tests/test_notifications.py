"""
Tests for Notification feature (Phase 5).
"""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from inventory.models import Warehouse, Product, Category, Unit, Batch
from security.models import Notification
from security.notification_service import NotificationService

User = get_user_model()


class NotificationModelTests(APITestCase):
    """Tests for Notification model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='notif_user',
            password='TestPass123!'
        )
        self.category = Category.objects.create(name='Test Category')
        self.unit = Unit.objects.create(name='Tablet', symbol='TAB')
        self.product = Product.objects.create(
            name='Test Product',
            generic_name='Test Generic',
            brand_name='Test Brand',
            category=self.category,
            unit=self.unit,
            strength='500mg',
            form='Tablet',
            manufacturer='Test Mfg',
            barcode='TEST123',
            sku='TEST-SKU',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Test Warehouse',
            code='TEST001',
            is_default=False
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number='BATCH-001',
            manufacturing_date=timezone.now().date() - timedelta(days=30),
            expiry_date=timezone.now().date() + timedelta(days=365),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            location=str(self.warehouse.id),
            is_active=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_notification(self):
        """Test creating a notification."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Low Stock Alert',
            message='Test message',
            severity='WARNING',
            product=self.product,
            warehouse=self.warehouse,
            batch=self.batch,
        )
        self.assertEqual(notification.notification_type, 'STOCK_LOW')
        self.assertEqual(notification.severity, 'WARNING')
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_mark_as_read(self):
        """Test marking notification as read."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test',
            message='Test message',
        )
        self.assertFalse(notification.is_read)
        
        notification.mark_as_read()
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_notification_type_choices(self):
        """Test notification type field accepts valid choices."""
        for type_choice, _ in Notification.TYPE_CHOICES:
            notification = Notification.objects.create(
                user=self.user,
                notification_type=type_choice,
                title=f'Test {type_choice}',
                message='Test message',
            )
            self.assertEqual(notification.notification_type, type_choice)

    def test_severity_choices(self):
        """Test severity field accepts valid choices."""
        for severity_choice, _ in Notification.SEVERITY_CHOICES:
            notification = Notification.objects.create(
                user=self.user,
                notification_type='STOCK_LOW',
                title='Test',
                message='Test message',
                severity=severity_choice,
            )
            self.assertEqual(notification.severity, severity_choice)


class NotificationServiceTests(APITestCase):
    """Tests for NotificationService."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='notif_service_user',
            password='TestPass123!'
        )
        self.category = Category.objects.create(name='Test Category')
        self.unit = Unit.objects.create(name='Tablet', symbol='TAB')
        self.product = Product.objects.create(
            name='Test Product',
            generic_name='Test Generic',
            brand_name='Test Brand',
            category=self.category,
            unit=self.unit,
            strength='500mg',
            form='Tablet',
            manufacturer='Test Mfg',
            barcode='TEST123',
            sku='TEST-SKU',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Test Warehouse',
            code='TEST002',
            is_default=False
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number='BATCH-SVC-001',
            manufacturing_date=timezone.now().date() - timedelta(days=30),
            expiry_date=timezone.now().date() + timedelta(days=365),
            purchase_price=Decimal('10.00'),
            sale_price=Decimal('15.00'),
            quantity=Decimal('100.00'),
            remaining_quantity=Decimal('100.00'),
            location=str(self.warehouse.id),
            is_active=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_notification(self):
        """Test creating a notification via service."""
        notification = NotificationService.create_notification(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test Notification',
            message='This is a test',
            severity='WARNING',
            product=self.product,
            warehouse=self.warehouse,
            batch=self.batch,
        )
        self.assertEqual(notification.notification_type, 'STOCK_LOW')
        self.assertEqual(notification.title, 'Test Notification')
        self.assertEqual(notification.severity, 'WARNING')

    def test_notify_low_stock(self):
        """Test low stock notification."""
        notification = NotificationService.notify_low_stock(
            user=self.user,
            batch=self.batch,
            current_qty=Decimal('5.00'),
            threshold=10,
        )
        self.assertEqual(notification.notification_type, 'STOCK_LOW')
        self.assertEqual(notification.severity, 'WARNING')
        self.assertIn('5', notification.message)

    def test_notify_expiring_batch(self):
        """Test expiring batch notification."""
        notification = NotificationService.notify_expiring_batch(
            user=self.user,
            batch=self.batch,
            days_until_expiry=14,
        )
        self.assertEqual(notification.notification_type, 'STOCK_EXPIRY')
        # 14 days should be WARNING (not critical)
        self.assertEqual(notification.severity, 'WARNING')

    def test_notify_expiring_batch_critical(self):
        """Test expiring batch notification with critical severity."""
        notification = NotificationService.notify_expiring_batch(
            user=self.user,
            batch=self.batch,
            days_until_expiry=3,
        )
        self.assertEqual(notification.notification_type, 'STOCK_EXPIRY')
        self.assertEqual(notification.severity, 'CRITICAL')

    def test_notify_out_of_stock(self):
        """Test out of stock notification."""
        notification = NotificationService.notify_out_of_stock(
            user=self.user,
            product=self.product,
            warehouse=self.warehouse,
        )
        self.assertEqual(notification.notification_type, 'STOCK_OUT')
        self.assertEqual(notification.severity, 'ERROR')

    def test_notify_user_login(self):
        """Test user login notification."""
        notification = NotificationService.notify_user_login(
            user=self.user,
            ip_address='192.168.1.1',
        )
        self.assertEqual(notification.notification_type, 'ACTIVITY_LOGIN')
        self.assertIn('192.168.1.1', notification.message)

    def test_get_unread_count(self):
        """Test getting unread count."""
        # Create some notifications
        NotificationService.create_notification(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test 1',
            message='Test message 1',
        )
        NotificationService.create_notification(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test 2',
            message='Test message 2',
        )
        
        count = NotificationService.get_unread_count(self.user)
        self.assertEqual(count, 2)

    def test_mark_as_read(self):
        """Test marking a notification as read."""
        notification = NotificationService.create_notification(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test',
            message='Test message',
        )
        
        success = NotificationService.mark_as_read(notification.id, self.user)
        self.assertTrue(success)
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_all_as_read(self):
        """Test marking all notifications as read."""
        # Create multiple notifications
        for i in range(3):
            NotificationService.create_notification(
                user=self.user,
                notification_type='STOCK_LOW',
                title=f'Test {i}',
                message=f'Test message {i}',
            )
        
        count = NotificationService.mark_all_as_read(self.user)
        self.assertEqual(count, 3)
        
        unread = NotificationService.get_unread_count(self.user)
        self.assertEqual(unread, 0)


class NotificationAPITests(APITestCase):
    """Tests for Notification API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='api_notif_user',
            password='TestPass123!'
        )
        self.category = Category.objects.create(name='API Category')
        self.unit = Unit.objects.create(name='Tablet', symbol='TAB')
        self.product = Product.objects.create(
            name='API Product',
            generic_name='API Generic',
            brand_name='API Brand',
            category=self.category,
            unit=self.unit,
            strength='500mg',
            form='Tablet',
            manufacturer='API Mfg',
            barcode='API123',
            sku='API-SKU',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='API Warehouse',
            code='API001',
            is_default=False
        )
        self.client.force_authenticate(user=self.user)

    def test_notifications_list(self):
        """Test getting notifications list."""
        Notification.objects.create(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test Notification',
            message='Test message',
        )

        response = self.client.get('/api/auth/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.data)
        self.assertTrue(isinstance(response.data['data'], list))

    def test_notifications_filter_by_read(self):
        """Test filtering notifications by read status."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test',
            message='Test',
        )
        notification.mark_as_read()
        
        # Get unread only
        response = self.client.get('/api/auth/notifications/?is_read=true')
        self.assertEqual(response.status_code, 200)

    def test_mark_notification_read(self):
        """Test marking a notification as read via API."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test',
            message='Test',
        )
        
        response = self.client.post('/api/auth/notifications/read/', {
            'notification_id': notification.id
        })
        self.assertEqual(response.status_code, 200)
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_all_notifications_read(self):
        """Test marking all notifications as read."""
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                notification_type='STOCK_LOW',
                title=f'Test {i}',
                message=f'Test {i}',
            )

        response = self.client.post('/api/auth/notifications/read/', {
            'mark_all': True
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['marked_count'], 3)

    def test_unread_count_endpoint(self):
        """Test unread count endpoint."""
        Notification.objects.create(
            user=self.user,
            notification_type='STOCK_LOW',
            title='Test',
            message='Test',
        )

        response = self.client.get('/api/auth/notifications/unread-count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['unread_count'], 1)