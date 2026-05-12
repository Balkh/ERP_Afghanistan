"""
Tests for the read-only observability API endpoints.
"""
import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User


class ObservabilityAPIBaseTest(APITestCase):
    """Base test class for observability API tests."""
    
    ENDPOINTS = [
        'obs-health',
        'obs-state', 
        'obs-timeline',
        'obs-incidents',
        'obs-dashboard',
        'obs-drift',
        'obs-replay-sessions',
        'obs-digital-twin',
        'obs-safety',
    ]
    
    def setUp(self):
        self.client = APIClient()
        self.client.logout()
        self.user = User.objects.create_user(username='obsuser', password='test123')
        self.client.force_authenticate(user=self.user)
    
    def _get_url(self, endpoint_name):
        """Get URL for named endpoint."""
        return reverse(endpoint_name)
    
    def test_all_endpoints_require_auth(self):
        """All observability endpoints must require authentication."""
        for endpoint in self.ENDPOINTS:
            self.client.force_authenticate(user=None)
            url = self._get_url(endpoint)
            response = self.client.get(url)
            self.assertIn(
                response.status_code, 
                [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                f"Endpoint {endpoint} should require auth, got {response.status_code}"
            )
            self.client.force_authenticate(user=self.user)
    
    def test_all_endpoints_return_200_for_auth(self):
        """All endpoints return 200 for authenticated users."""
        for endpoint in self.ENDPOINTS:
            url = self._get_url(endpoint)
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 
                status.HTTP_200_OK,
                f"Endpoint {endpoint} should return 200, got {response.status_code}"
            )
    
    def test_response_structure(self):
        """All endpoints return standardized response structure."""
        for endpoint in self.ENDPOINTS:
            url = self._get_url(endpoint)
            response = self.client.get(url)
            data = response.json()
            self.assertIn('success', data, f"{endpoint}: missing 'success'")
            self.assertIn('data', data, f"{endpoint}: missing 'data'")
            self.assertIn('meta', data, f"{endpoint}: missing 'meta'")
    
    def test_meta_read_only_flag(self):
        """All responses must have read_only: true in meta."""
        for endpoint in self.ENDPOINTS:
            url = self._get_url(endpoint)
            response = self.client.get(url)
            data = response.json()
            meta = data.get('meta', {})
            self.assertTrue(
                meta.get('read_only', False),
                f"{endpoint}: meta.read_only should be True"
            )
    
    def test_rejects_post(self):
        """All endpoints reject POST requests."""
        for endpoint in self.ENDPOINTS:
            url = self._get_url(endpoint)
            response = self.client.post(url, {})
            self.assertIn(
                response.status_code,
                [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED],
                f"Endpoint {endpoint} should reject POST, got {response.status_code}"
            )
    
    def test_rejects_put(self):
        """All endpoints reject PUT requests."""
        for endpoint in self.ENDPOINTS:
            url = self._get_url(endpoint)
            response = self.client.put(url, {})
            self.assertIn(
                response.status_code,
                [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED],
                f"Endpoint {endpoint} should reject PUT, got {response.status_code}"
            )
    
    def test_rejects_delete(self):
        """All endpoints reject DELETE requests."""
        for endpoint in self.ENDPOINTS:
            url = self._get_url(endpoint)
            response = self.client.delete(url)
            self.assertIn(
                response.status_code,
                [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED],
                f"Endpoint {endpoint} should reject DELETE, got {response.status_code}"
            )
    
    def test_health_endpoint_details(self):
        """Health endpoint returns status info."""
        url = self._get_url('obs-health')
        response = self.client.get(url)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('status', data['data'])
        self.assertIn('version', data['data'])


class ObservabilityAPITimelineTest(APITestCase):
    """Specific tests for timeline endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='timelineuser', password='test123')
        self.client.force_authenticate(user=self.user)
    
    def test_timeline_accepts_limit_param(self):
        """Timeline endpoint accepts limit parameter."""
        url = reverse('obs-timeline')
        response = self.client.get(url, {'limit': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_timeline_accepts_offset_param(self):
        """Timeline endpoint accepts offset parameter."""
        url = reverse('obs-timeline')
        response = self.client.get(url, {'offset': 0})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_timeline_negative_limit_safe(self):
        """Timeline handles negative limit safely."""
        url = reverse('obs-timeline')
        response = self.client.get(url, {'limit': -1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ObservabilityAPIIncidentsTest(APITestCase):
    """Specific tests for incidents endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='incuser', password='test123')
        self.client.force_authenticate(user=self.user)
    
    def test_incidents_accepts_filters(self):
        """Incidents endpoint accepts severity and status filters."""
        url = reverse('obs-incidents')
        response = self.client.get(url, {'severity': 'HIGH', 'status': 'OPEN', 'limit': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_incidents_invalid_severity_safe(self):
        """Incidents endpoint handles invalid severity gracefully."""
        url = reverse('obs-incidents')
        response = self.client.get(url, {'severity': 'INVALID_SEVERITY'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ObservabilityAPIReplayTest(APITestCase):
    """Specific tests for replay endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='replayuser', password='test123')
        self.client.force_authenticate(user=self.user)


class ObservabilityPermissionTest(APITestCase):
    """Test permission enforcement."""
    
    def setUp(self):
        self.client = APIClient()
        self.client.logout()
        self.observer = User.objects.create_user(username='observer', password='test123')
        self.admin = User.objects.create_superuser(username='obsadmin', password='test123', email='a@a.com')
    
    def test_unauthenticated_blocked(self):
        """Unauthenticated users are blocked."""
        url = reverse('obs-health')
        response = self.client.get(url)
        self.assertIn(response.status_code, [401, 403])
    
    def test_authenticated_observer_allowed(self):
        """Authenticated users can access observability endpoints."""
        self.client.force_authenticate(user=self.observer)
        url = reverse('obs-health')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
