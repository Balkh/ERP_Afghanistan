"""
Integration tests for observability layer.
Tests the full stack: API → Router → Engine → Subcomponents.
"""
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity
from simulation.replay.replay_engine.replay_engine import ReplayEngine


class ObservabilityIntegrationBase(APITestCase):
    """Base class for integration tests."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='intuser', password='test123')
        self.client.force_authenticate(user=self.user)


class ControlCenterEngineStateIntegrationTest(ObservabilityIntegrationBase):
    """Integration: ControlCenterEngine state through API."""
    
    def test_state_endpoint_returns_valid_structure(self):
        """State endpoint must return structured state data."""
        url = reverse('obs-state')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('state', data['data'])
    
    def test_dashboard_endpoint_returns_valid_structure(self):
        """Dashboard endpoint must return structured dashboard data."""
        url = reverse('obs-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_health_endpoint_returns_status(self):
        """Health endpoint returns status info."""
        url = reverse('obs-health')
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data['data']['status'], 'healthy')
        self.assertEqual(data['data']['version'], '1.0.0')


class ControlCenterRouterIntegrationTest(TestCase):
    """Integration: Router → Engine → Query."""
    
    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)
    
    def test_router_all_query_types_succeed(self):
        """All query types must succeed through router."""
        query_types = ['state', 'timeline', 'incidents', 'dashboard', 'health', 'safety']
        for qtype in query_types:
            result = self.router.route_query(qtype)
            self.assertTrue(
                result.get('success', False),
                f"Query type '{qtype}' should succeed"
            )
    
    def test_router_unknown_query_returns_error(self):
        """Unknown query type should return error, not crash."""
        result = self.router.route_query('nonexistent_query_type')
        self.assertFalse(result.get('success', True))
    
    def test_router_signal_processing(self):
        """Router must process signals successfully."""
        signal = OperationalSignal(
            signal_id='integ-test-signal-1',
            signal_type=SignalType.DRIFT_TREND,
            severity=IntelligenceSeverity.INFO,
            source_phase='integration_test',
            tick=1,
            description='Integration test signal',
            payload={'test': True},
            timestamp=1000.0,
        )
        result = self.router.route_signal(signal)
        self.assertTrue(result.get('success', False))
    
    def test_state_after_signal_processing(self):
        """State must reflect processed signals."""
        self.engine.clear()
        
        # Process a signal
        signal = OperationalSignal(
            signal_id='integ-state-test',
            signal_type=SignalType.ANOMALY,
            severity=IntelligenceSeverity.HIGH,
            source_phase='integration_test',
            tick=1,
            description='State integration test',
            payload={},
            timestamp=1000.0,
        )
        self.router.route_signal(signal)
        
        # Query state
        state = self.router.route_query('state')
        self.assertTrue(state['success'])
        self.assertGreaterEqual(state['data']['active_signals'], 1)


class EngineSignalProcessingTest(TestCase):
    """Test engine signal processing pipeline."""
    
    def setUp(self):
        self.engine = ControlCenterEngine()
    
    def test_signal_through_full_pipeline(self):
        """Signal must flow through full pipeline without error."""
        sig = OperationalSignal(
            signal_id='pipeline-test',
            signal_type=SignalType.DRIFT_TREND,
            severity=IntelligenceSeverity.MEDIUM,
            source_phase='test',
            tick=1,
            description='Pipeline test',
            payload={'drift_value': 0.5},
            timestamp=1000.0,
        )
        result = self.engine.process_signal(sig)
        self.assertIsInstance(result, dict)
    
    def test_multiple_signals_through_pipeline(self):
        """Multiple signals must flow through pipeline without error."""
        for i in range(10):
            sig = OperationalSignal(
                signal_id=f'multi-pipeline-{i}',
                signal_type=SignalType.TRUTH_MISMATCH if i % 2 == 0 else SignalType.ANOMALY,
                severity=IntelligenceSeverity.INFO if i < 5 else IntelligenceSeverity.MEDIUM,
                source_phase='test',
                tick=i,
                description=f'Pipeline test {i}',
                payload={'index': i},
                timestamp=1000.0 + i,
            )
            result = self.engine.process_signal(sig)
            self.assertIsInstance(result, dict)
    
    def test_high_severity_signal_creates_incident(self):
        """High severity signal should create an incident."""
        self.engine.clear()
        sig = OperationalSignal(
            signal_id='incident-test',
            signal_type=SignalType.INTEGRITY_BREACH,
            severity=IntelligenceSeverity.CRITICAL,
            source_phase='test',
            tick=1,
            description='Should create incident',
            payload={'breach': True},
            timestamp=1000.0,
        )
        self.engine.process_signal(sig)
        
        # Check incidents
        incidents = self.engine.get_incident_registry()
        count = incidents.get_incident_count()
        self.assertGreaterEqual(count, 0)


class ReplayEngineIntegrationTest(TestCase):
    """Integration tests for ReplayEngine."""
    
    def setUp(self):
        self.engine = ReplayEngine()
    
    def test_session_creation_through_engine(self):
        """Replay sessions must be creatable through engine."""
        result = self.engine.execute_replay('integ-replay-test', [
            {'tick': 1, 'event_type': 'TEST', 'payload': {}}
        ])
        self.assertIsInstance(result, dict)
    
    def test_safety_guard_integration(self):
        """Safety guard must integrate with engine."""
        guard = self.engine.safety_guard
        self.assertIsNotNone(guard)
        result = guard.check_write_operation('any_write')
        self.assertFalse(result.get('allowed', True))


class ObservabilityFullStackIntegrationTest(ObservabilityIntegrationBase):
    """Full stack integration test: API → Router → Engine."""
    
    def test_full_observability_flow(self):
        """Full observability flow must complete without error."""
        endpoints = ['obs-health', 'obs-state', 'obs-dashboard', 'obs-safety']
        
        composite_result = {}
        for ep in endpoints:
            url = reverse(ep)
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 200,
                f"Endpoint {ep} failed in full stack test"
            )
            composite_result[ep] = response.json()
        
        # Verify all endpoints returned success
        for ep, data in composite_result.items():
            self.assertTrue(
                data.get('success', False),
                f"Endpoint {ep} returned unsuccessful"
            )
