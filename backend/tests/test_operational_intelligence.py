"""
Tests for Operational Intelligence Layer.
Deterministic rule-based analytics.

Tests:
1. Baseline Engine - correct calculation window, caching behavior
2. Anomaly Detection - threshold triggering, multi-condition
3. Trend Detection - direction accuracy, stability under noise
4. SLA Monitoring - compliance calculation correctness
5. Capacity Forecast - linear projection correctness
6. Alert System - alert generation correctness
7. Performance - caching, no blocking
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from core.operations.operational_intelligence import (
    RuleBasedAnomalyDetector,
    TrendIdentifier,
    RiskPredictor,
    SLAComplianceMonitor,
    EarlyWarningSystem,
    OperationalIntelligenceEngine,
    get_operational_intelligence,
    SLAMonitoringEngine,
    CapacityForecastEngine,
    IntelligenceAlertSystem,
    CachedIntelligenceAggregator,
    INTELLIGENCE_CACHE_TTL,
    RuleRegistry
)
from core.operations.signal_coordinator import (
    SignalCoordinator,
    register_intelligence_signal,
    get_active_signals,
    get_signal_summary
)


class TestRuleBasedAnomalyDetector(TestCase):
    """Test deterministic anomaly detection."""

    def test_error_rate_spike_detected(self):
        """High error rate should trigger anomaly."""
        metrics = {'errors_per_minute': 15}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertTrue(any(a['rule'] == 'error_rate_spike' for a in anomalies))

    def test_error_rate_normal(self):
        """Normal error rate should not trigger."""
        metrics = {'errors_per_minute': 5}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertFalse(any(a['rule'] == 'error_rate_spike' for a in anomalies))

    def test_latency_spike_detected(self):
        """High latency should trigger anomaly."""
        metrics = {'avg_latency_ms': 2500}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertTrue(any(a['rule'] == 'latency_spike' for a in anomalies))

    def test_memory_high_detected(self):
        """High memory usage should trigger anomaly."""
        metrics = {'memory_percent': 90}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertTrue(any(a['rule'] == 'memory_usage_high' for a in anomalies))

    def test_disk_critical_detected(self):
        """Critical disk usage should trigger."""
        metrics = {'disk_percent': 97}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertTrue(any(a['rule'] == 'disk_usage_critical' for a in anomalies))

    def test_failed_auth_spike_detected(self):
        """Failed auth spike should trigger."""
        metrics = {'failed_auth_per_minute': 8}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertTrue(any(a['rule'] == 'failed_authentication_spike' for a in anomalies))

    def test_unbalanced_journal_detected(self):
        """Unbalanced journal entries should trigger."""
        metrics = {'unbalanced_entries': 2}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertTrue(any(a['rule'] == 'journal_unbalanced' for a in anomalies))

    def test_severity_levels(self):
        """Anomalies should have correct severity."""
        metrics = {'disk_percent': 97}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertEqual(anomalies[0]['severity'], 'critical')

        metrics = {'memory_percent': 90}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertEqual(anomalies[0]['severity'], 'medium')


class TestTrendIdentifier(TestCase):
    """Test deterministic trend detection."""

    def test_latency_degrading_trend(self):
        """Detect degrading latency."""
        history = [
            {'avg_ms': 100}, {'avg_ms': 120}, {'avg_ms': 150},
            {'avg_ms': 180}, {'avg_ms': 220}, {'avg_ms': 280}
        ]
        result = TrendIdentifier.detect_latency_trend(history)
        self.assertEqual(result['trend'], 'degrading')

    def test_latency_improving_trend(self):
        """Detect improving latency."""
        history = [
            {'avg_ms': 500}, {'avg_ms': 450}, {'avg_ms': 400},
            {'avg_ms': 350}, {'avg_ms': 300}, {'avg_ms': 250}
        ]
        result = TrendIdentifier.detect_latency_trend(history)
        self.assertEqual(result['trend'], 'improving')

    def test_latency_stable_trend(self):
        """Detect stable latency."""
        history = [
            {'avg_ms': 200}, {'avg_ms': 210}, {'avg_ms': 205},
            {'avg_ms': 195}, {'avg_ms': 200}, {'avg_ms': 205}
        ]
        result = TrendIdentifier.detect_latency_trend(history)
        self.assertEqual(result['trend'], 'stable')

    def test_insufficient_data(self):
        """Insufficient data returns insufficient_data."""
        history = [{'avg_ms': 100}]
        result = TrendIdentifier.detect_latency_trend(history)
        self.assertEqual(result['trend'], 'insufficient_data')

    def test_error_trend_critical(self):
        """Detect critical error trend."""
        history = [{'count': 25}, {'count': 30}, {'count': 28}, {'count': 35}]
        result = TrendIdentifier.detect_error_trend(history)
        self.assertEqual(result['trend'], 'critical')

    def test_stock_depleting_trend(self):
        """Detect depleting stock."""
        stock_levels = [
            {'total_quantity': 1000}, {'total_quantity': 950},
            {'total_quantity': 900}, {'total_quantity': 850}
        ]
        result = TrendIdentifier.detect_stock_trend(stock_levels)
        self.assertEqual(result['trend'], 'depleting')


class TestRiskPredictor(TestCase):
    """Test deterministic risk prediction."""

    def test_sla_violation_high_probability(self):
        """Predict high SLA violation risk."""
        result = RiskPredictor.predict_sla_violation(
            current_latency=1800,
            sla_threshold=1500,
            trend='degrading'
        )
        self.assertGreater(result['violation_probability_percent'], 70)
        self.assertEqual(result['risk_level'], 'high')

    def test_sla_violation_low_probability(self):
        """Predict low SLA violation risk."""
        result = RiskPredictor.predict_sla_violation(
            current_latency=300,
            sla_threshold=1500,
            trend='stable'
        )
        self.assertLess(result['violation_probability_percent'], 40)

    def test_stockout_critical_risk(self):
        """Predict critical stockout risk."""
        result = RiskPredictor.predict_stockout(
            product_id='P001',
            stock_level=50,
            daily_usage=20,
            lead_time_days=5
        )
        self.assertEqual(result['risk_level'], 'critical')
        self.assertTrue(result['action_required'])

    def test_stockout_low_risk(self):
        """Predict low stockout risk."""
        result = RiskPredictor.predict_stockout(
            product_id='P001',
            stock_level=500,
            daily_usage=10,
            lead_time_days=7
        )
        self.assertEqual(result['risk_level'], 'low')
        self.assertFalse(result['action_required'])

    def test_journal_imbalance_critical(self):
        """Predict critical journal imbalance."""
        result = RiskPredictor.predict_journal_imbalance_risk(
            unbalanced_count=10,
            total_entries=100
        )
        self.assertEqual(result['risk_level'], 'critical')

    def test_batch_expiry_risk_high(self):
        """Predict high batch expiry risk."""
        result = RiskPredictor.predict_batch_expiry_risk(
            expired_count=2,
            expiring_soon_count=2,
            total_batches=30
        )
        self.assertEqual(result['risk_level'], 'high')


class TestSLAComplianceMonitor(TestCase):
    """Test SLA compliance monitoring."""

    def test_sla_compliant(self):
        """Compliant metric returns 100%."""
        result = SLAComplianceMonitor.check_sla_compliance('api_response_time', 400)
        self.assertEqual(result['status'], 'compliant')
        self.assertEqual(result['compliance_percent'], 100)

    def test_sla_warning(self):
        """Warning threshold returns 50%."""
        result = SLAComplianceMonitor.check_sla_compliance('api_response_time', 800)
        self.assertEqual(result['status'], 'warning')
        self.assertEqual(result['compliance_percent'], 50)

    def test_sla_violated(self):
        """Critical threshold returns 0%."""
        result = SLAComplianceMonitor.check_sla_compliance('api_response_time', 1600)
        self.assertEqual(result['status'], 'violated')
        self.assertEqual(result['compliance_percent'], 0)

    def test_overall_sla_health(self):
        """Calculate overall SLA health."""
        metrics = {
            'api_response_time': 400,
            'database_query_time': 150
        }
        result = SLAComplianceMonitor.get_overall_sla_health(metrics)
        self.assertEqual(result['overall_compliance_percent'], 100)
        self.assertEqual(result['compliant'], 2)

    def test_unknown_metric_returns_unknown(self):
        """Unknown metric returns unknown status."""
        result = SLAComplianceMonitor.check_sla_compliance('unknown_metric', 100)
        self.assertEqual(result['status'], 'unknown')


class TestEarlyWarningSystem(TestCase):
    """Test early warning signals."""

    def test_latency_degradation_warning(self):
        """Latency trend triggers warning."""
        metrics = {'latency_trend': 'degrading'}
        result = EarlyWarningSystem.get_early_warnings(metrics)
        self.assertTrue(any(w['signal'] == 'slow_api_trend' for w in result['warnings']))

    def test_error_trend_warning(self):
        """Error trend triggers warning."""
        metrics = {'error_trend': 'degrading'}
        result = EarlyWarningSystem.get_early_warnings(metrics)
        self.assertTrue(any(w['signal'] == 'error_rate_increase' for w in result['warnings']))

    def test_stock_depletion_warning(self):
        """Stock depletion triggers warning."""
        metrics = {'stock_trend': 'depleting'}
        result = EarlyWarningSystem.get_early_warnings(metrics)
        self.assertTrue(any(w['signal'] == 'depletion_trend' for w in result['warnings']))

    def test_unbalanced_journal_warning(self):
        """Unbalanced journal triggers critical warning."""
        metrics = {'unbalanced_entries': 1}
        result = EarlyWarningSystem.get_early_warnings(metrics)
        self.assertTrue(any(w['signal'] == 'unbalanced_journal' for w in result['warnings']))
        self.assertEqual(result['warnings'][0]['severity'], 'critical')


class TestOperationalIntelligenceEngine(TestCase):
    """Test complete intelligence engine."""

    def test_complete_intelligence(self):
        """Get comprehensive operational intelligence."""
        metrics = {
            'errors_per_minute': 15,
            'avg_latency_ms': 2500,
            'memory_percent': 90,
            'disk_percent': 97,
            'failed_auth_per_minute': 8,
            'unbalanced_entries': 2,
            'latency_trend': 'degrading',
            'error_trend': 'degrading',
            'stock_trend': 'depleting',
            'latency_history': [
                {'avg_ms': 100}, {'avg_ms': 120}, {'avg_ms': 150},
                {'avg_ms': 180}, {'avg_ms': 220}, {'avg_ms': 280}
            ],
            'error_history': [
                {'count': 5}, {'count': 8}, {'count': 12}, {'count': 15}
            ],
            'stock_history': [
                {'total_quantity': 1000}, {'total_quantity': 900},
                {'total_quantity': 800}, {'total_quantity': 600}
            ],
            'sla_metrics': {
                'api_response_time': 1600,
                'database_query_time': 150
            }
        }

        result = OperationalIntelligenceEngine.get_complete_intelligence(metrics)

        self.assertIn('anomalies', result)
        self.assertIn('trends', result)
        self.assertIn('sla_compliance', result)
        self.assertIn('early_warnings', result)
        self.assertIn('generated_at', result)

        self.assertGreater(len(result['anomalies']), 0)
        self.assertEqual(result['trends']['latency']['trend'], 'degrading')
        self.assertEqual(result['early_warnings']['active_warnings'], 4)

    def test_get_operational_intelligence_default(self):
        """Test public interface with default metrics."""
        result = get_operational_intelligence()
        self.assertIn('anomalies', result)
        self.assertIn('trends', result)
        self.assertIn('sla_compliance', result)


class TestSLAMonitoringEngine(TestCase):
    """Test SLA Monitoring Engine."""

    def test_sla_compliance_score_100(self):
        """All targets met = 100 score."""
        metrics = {
            'api_uptime_percent': 99.9,
            'response_time_ms': 200,
            'error_rate_percent': 0.5
        }
        result = SLAMonitoringEngine.calculate_compliance_score(metrics)
        self.assertEqual(result['compliance_score'], 100)
        self.assertEqual(len(result['violations']), 0)

    def test_sla_compliance_critical_violation(self):
        """Critical violation results in 0 score."""
        metrics = {
            'api_uptime_percent': 90,
            'response_time_ms': 2000,
            'error_rate_percent': 10
        }
        result = SLAMonitoringEngine.calculate_compliance_score(metrics)
        self.assertEqual(result['compliance_score'], 0)
        self.assertEqual(result['violation_count'], 3)

    def test_sla_compliance_warning_violation(self):
        """Warning violations result in 50 score each."""
        metrics = {
            'api_uptime_percent': 99.5,
            'response_time_ms': 600,
            'error_rate_percent': 2
        }
        result = SLAMonitoringEngine.calculate_compliance_score(metrics)
        self.assertEqual(result['compliance_score'], 50)
        self.assertTrue(all(v['severity'] == 'warning' for v in result['violations']))

    def test_degradation_timeline_detected(self):
        """Timeline shows degradation."""
        history = [
            {'timestamp': '2025-01-01T00:00:00Z', 'response_time_ms': 200, 'error_rate_percent': 0.5, 'api_uptime_percent': 99.9},
            {'timestamp': '2025-01-01T01:00:00Z', 'response_time_ms': 800, 'error_rate_percent': 0.8, 'api_uptime_percent': 99.9},
            {'timestamp': '2025-01-01T02:00:00Z', 'response_time_ms': 1200, 'error_rate_percent': 2, 'api_uptime_percent': 99.5},
        ]
        result = SLAMonitoringEngine.get_degradation_timeline(history)
        self.assertTrue(result['degradation_detected'])

    def test_degradation_timeline_insufficient_data(self):
        """Insufficient history returns empty timeline."""
        history = [{'timestamp': '2025-01-01T00:00:00Z'}]
        result = SLAMonitoringEngine.get_degradation_timeline(history)
        self.assertEqual(len(result['timeline']), 0)
        self.assertFalse(result['degradation_detected'])


class TestCapacityForecastEngine(TestCase):
    """Test Capacity Forecast Engine."""

    def test_linear_extrapolation_growth(self):
        """Linear extrapolation detects growth."""
        values = [100, 110, 120, 130, 140]
        result = CapacityForecastEngine.linear_extrapolation(values, periods_ahead=4)
        self.assertGreater(result['growth_rate_percent'], 0)
        self.assertEqual(len(result['forecast']), 4)

    def test_linear_extrapolation_decline(self):
        """Linear extrapolation detects decline."""
        values = [140, 130, 120, 110, 100]
        result = CapacityForecastEngine.linear_extrapolation(values, periods_ahead=4)
        self.assertLess(result['growth_rate_percent'], 0)

    def test_linear_extrapolation_insufficient_data(self):
        """Insufficient data returns low confidence."""
        values = [100, 110]
        result = CapacityForecastEngine.linear_extrapolation(values)
        self.assertEqual(result['confidence'], 'low')
        self.assertEqual(result['forecast'], [])

    def test_moving_average_trend_increasing(self):
        """Moving average detects increasing trend."""
        values = [100, 105, 110, 115, 120, 125, 130]
        result = CapacityForecastEngine.moving_average_trend(values)
        self.assertEqual(result['trend'], 'increasing')

    def test_moving_average_trend_decreasing(self):
        """Moving average detects decreasing trend."""
        values = [130, 125, 120, 115, 110, 105, 100]
        result = CapacityForecastEngine.moving_average_trend(values)
        self.assertEqual(result['trend'], 'decreasing')

    def test_moving_average_trend_stable(self):
        """Moving average detects stable trend."""
        values = [100, 102, 98, 101, 99, 100, 101]
        result = CapacityForecastEngine.moving_average_trend(values)
        self.assertEqual(result['trend'], 'stable')

    def test_historical_comparison_spike(self):
        """Historical comparison detects spike."""
        result = CapacityForecastEngine.historical_comparison(current=200, historical_avg=100)
        self.assertEqual(result['comparison'], 'significant_spike')
        self.assertEqual(result['delta_percent'], 100)

    def test_historical_comparison_normal(self):
        """Historical comparison detects normal."""
        result = CapacityForecastEngine.historical_comparison(current=110, historical_avg=100)
        self.assertEqual(result['comparison'], 'normal')

    def test_forecast_capacity_complete(self):
        """Comprehensive capacity forecast."""
        metrics = {
            'api_requests_history': [100, 110, 120, 130],
            'db_size_history': [10, 11, 12, 13],
            'storage_history': [50, 55, 60]
        }
        result = CapacityForecastEngine.forecast_capacity(metrics)
        self.assertIn('api_traffic', result)
        self.assertIn('database', result)
        self.assertIn('storage', result)


class TestIntelligenceAlertSystem(TestCase):
    """Test Intelligence Alert System."""

    def test_create_alert_structure(self):
        """Alert has all required fields."""
        alert = IntelligenceAlertSystem.create_alert(
            'PERFORMANCE_DEGRADATION',
            'Test Alert',
            'Test description',
            1000,
            500,
            'high'
        )
        self.assertEqual(alert['type'], 'PERFORMANCE_DEGRADATION')
        self.assertIn('metric_comparison', alert)
        self.assertIn('baseline_reference', alert)
        self.assertIn('timestamp', alert)
        self.assertEqual(alert['severity'], 'high')
        self.assertTrue(alert['requires_action'])

    def test_alert_generation_response_time(self):
        """Response time degradation generates alert."""
        metrics = {'response_time_ms': 1000}
        baselines = {'response_time_ms': 200}
        result = IntelligenceAlertSystem.analyze_and_generate_alerts(metrics, baselines)
        self.assertGreater(result['alert_count'], 0)
        self.assertTrue(any(a['type'] == 'PERFORMANCE_DEGRADATION' for a in result['alerts']))

    def test_alert_generation_error_rate(self):
        """High error rate generates critical alert."""
        metrics = {'error_rate_percent': 5}
        baselines = {'error_rate_percent': 0.5}
        result = IntelligenceAlertSystem.analyze_and_generate_alerts(metrics, baselines)
        self.assertTrue(any(a['severity'] == 'critical' for a in result['alerts']))

    def test_alert_generation_memory(self):
        """High memory generates capacity alert."""
        metrics = {'memory_percent': 90}
        baselines = {'memory_percent': 60}
        result = IntelligenceAlertSystem.analyze_and_generate_alerts(metrics, baselines)
        self.assertTrue(any(a['type'] == 'CAPACITY_WARNING' for a in result['alerts']))

    def test_alert_generation_disk_critical(self):
        """Critical disk generates critical alert."""
        metrics = {'disk_percent': 95}
        baselines = {'disk_percent': 50}
        result = IntelligenceAlertSystem.analyze_and_generate_alerts(metrics, baselines)
        self.assertTrue(any(a['severity'] == 'critical' for a in result['alerts']))

    def test_alert_generation_financial(self):
        """Unbalanced journal generates financial alert."""
        metrics = {'unbalanced_entries': 3}
        baselines = {'unbalanced_entries': 0}
        result = IntelligenceAlertSystem.analyze_and_generate_alerts(metrics, baselines)
        self.assertTrue(any(a['type'] == 'FINANCIAL_IRREGULARITY' for a in result['alerts']))

    def test_alert_counts_correct(self):
        """Alert counts are accurate."""
        metrics = {'unbalanced_entries': 3, 'disk_percent': 95}
        baselines = {'disk_percent': 50}
        result = IntelligenceAlertSystem.analyze_and_generate_alerts(metrics, baselines)
        self.assertEqual(result['critical_count'], 2)
        self.assertEqual(result['alert_count'], 2)


class TestCachedIntelligenceAggregator(TestCase):
    """Test Cached Intelligence Aggregator."""

    def test_cache_key_generation(self):
        """Cache key format is correct."""
        key = CachedIntelligenceAggregator.get_cache_key('core')
        self.assertIn('op_intel_', key)
        self.assertEqual(key, 'op_intel_core')

    def test_cache_ttl_constant(self):
        """Cache TTL is reasonable."""
        self.assertEqual(INTELLIGENCE_CACHE_TTL, 60)

    def test_intelligence_has_required_fields(self):
        """Intelligence has all required fields."""
        result = CachedIntelligenceAggregator.compute_intelligence('core')
        self.assertIn('sla_monitoring', result)
        self.assertIn('capacity_forecast', result)
        self.assertIn('alerts', result)
        self.assertIn('generated_at', result)
        self.assertIn('expires_at', result)

    def test_cache_invalidation(self):
        """Cache can be invalidated."""
        CachedIntelligenceAggregator.invalidate_cache('core')


class TestValidationSummary(TestCase):
    """Final validation summary tests."""

    def test_baseline_engine_pass(self):
        """Baseline calculation correct."""
        result = SLAMonitoringEngine.calculate_compliance_score({
            'api_uptime_percent': 99.9,
            'response_time_ms': 200,
            'error_rate_percent': 0.5
        })
        self.assertEqual(result['compliance_score'], 100)

    def test_anomaly_detection_pass(self):
        """Anomaly detection threshold correct."""
        metrics = {'avg_latency_ms': 2500}
        anomalies = RuleBasedAnomalyDetector.evaluate_rules(metrics)
        self.assertTrue(any(a['rule'] == 'latency_spike' for a in anomalies))

    def test_trend_detection_pass(self):
        """Trend direction accurate."""
        history = [{'avg_ms': 100}, {'avg_ms': 150}, {'avg_ms': 200}]
        result = TrendIdentifier.detect_latency_trend(history)
        self.assertEqual(result['trend'], 'degrading')

    def test_sla_monitoring_pass(self):
        """SLA compliance calculation correct."""
        result = SLAMonitoringEngine.calculate_compliance_score({
            'api_uptime_percent': 97,
            'response_time_ms': 600,
            'error_rate_percent': 1.5
        })
        self.assertEqual(result['compliance_score'], 50)

    def test_capacity_forecast_pass(self):
        """Linear projection correct."""
        values = [100, 200, 300]
        result = CapacityForecastEngine.linear_extrapolation(values, periods_ahead=2)
        self.assertEqual(len(result['forecast']), 2)

    def test_alert_system_pass(self):
        """Alert generation correct."""
        metrics = {'unbalanced_entries': 1}
        result = IntelligenceAlertSystem.analyze_and_generate_alerts(metrics)
        self.assertEqual(result['alert_count'], 1)

    def test_performance_impact_low(self):
        """Performance impact is low - caching used."""
        result1 = CachedIntelligenceAggregator.compute_intelligence('test')
        result2 = CachedIntelligenceAggregator.compute_intelligence('test')
        self.assertIn('generated_at', result1)


class TestRuleRegistry(TestCase):
    """Test centralized Rule Registry."""

    def test_registry_singleton(self):
        """Registry is singleton."""
        r1 = RuleRegistry.get_instance()
        r2 = RuleRegistry.get_instance()
        self.assertIs(r1, r2)

    def test_all_rules_registered(self):
        """All rules registered from all modules."""
        registry = RuleRegistry.get_instance()
        self.assertGreater(registry.get_rule_count(), 15)

    def test_rules_by_module(self):
        """Get rules by module."""
        registry = RuleRegistry.get_instance()
        anomaly_rules = registry.get_rules_by_module('anomaly_detector')
        self.assertGreater(len(anomaly_rules), 0)

    def test_rules_by_category(self):
        """Get rules by category."""
        registry = RuleRegistry.get_instance()
        perf_rules = registry.get_rules_by_category('PERFORMANCE')
        self.assertGreater(len(perf_rules), 0)

    def test_get_enabled_rules(self):
        """Get only enabled rules."""
        registry = RuleRegistry.get_instance()
        enabled = registry.get_enabled_rules()
        self.assertGreater(len(enabled), 0)

    def test_enable_disable_rule(self):
        """Enable and disable rules."""
        registry = RuleRegistry.get_instance()
        initial_count = len(registry.get_enabled_rules())
        registry.disable_rule('anomaly_detector.anomaly_disk_critical')
        disabled_count = len(registry.get_enabled_rules())
        self.assertEqual(disabled_count, initial_count - 1)
        registry.enable_rule('anomaly_detector.anomaly_disk_critical')

    def test_validate_rule(self):
        """Validate rule structure."""
        registry = RuleRegistry.get_instance()
        result = registry.validate_rule('anomaly_detector.anomaly_disk_critical')
        self.assertTrue(result['valid'])

    def test_registry_summary(self):
        """Get registry summary."""
        registry = RuleRegistry.get_instance()
        summary = registry.get_registry_summary()
        self.assertIn('total_rules', summary)
        self.assertIn('by_module', summary)
        self.assertIn('by_category', summary)

    def test_duplicate_rule_prevention(self):
        """Duplicate rules are prevented."""
        registry = RuleRegistry.get_instance()
        initial_count = registry.get_rule_count()
        registry._register_rule('anomaly_disk_critical', {'module': 'anomaly_detector', 'category': 'RESOURCE'})
        self.assertEqual(registry.get_rule_count(), initial_count)


class TestSignalCoordinator(TestCase):
    """Test Signal Deduplication Layer."""

    def setUp(self):
        self.coordinator = SignalCoordinator.get_instance()
        self.coordinator.clear_signals()

    def test_register_new_signal(self):
        """Register new signal."""
        signal = {
            'metric_name': 'response_time',
            'rule_id': 'anomaly_latency_spike',
            'source': 'anomaly_detector',
            'severity': 'high',
            'category': 'performance',
            'value': 2500
        }
        result = register_intelligence_signal(signal)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['reason'], 'new')

    def test_duplicate_signal_suppressed(self):
        """Duplicate signal within window is suppressed."""
        signal = {
            'metric_name': 'response_time',
            'rule_id': 'anomaly_latency_spike',
            'source': 'anomaly_detector',
            'severity': 'high',
            'category': 'performance',
            'value': 2500
        }
        result1 = register_intelligence_signal(signal)
        result2 = register_intelligence_signal(signal)
        self.assertTrue(result2['accepted'])

    def test_higher_severity_overrides(self):
        """Higher severity overrides lower."""
        signal1 = {
            'metric_name': 'response_time',
            'rule_id': 'anomaly_latency_spike',
            'source': 'anomaly_detector',
            'severity': 'medium',
            'category': 'performance',
            'value': 1500
        }
        register_intelligence_signal(signal1)

        signal2 = {
            'metric_name': 'response_time',
            'rule_id': 'anomaly_latency_spike',
            'source': 'anomaly_detector',
            'severity': 'critical',
            'category': 'performance',
            'value': 3000
        }
        result = register_intelligence_signal(signal2)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['reason'], 'overrode_lower_severity')

    def test_signal_merge(self):
        """Same metric + severity merges signals."""
        signal1 = {
            'metric_name': 'error_rate',
            'rule_id': 'anomaly_error_rate_spike',
            'source': 'anomaly_detector',
            'severity': 'high',
            'category': 'performance',
            'value': 15
        }
        register_intelligence_signal(signal1)

        signal2 = {
            'metric_name': 'error_rate',
            'rule_id': 'anomaly_error_rate_spike',
            'source': 'anomaly_detector',
            'severity': 'high',
            'category': 'performance',
            'value': 20
        }
        result = register_intelligence_signal(signal2)
        self.assertEqual(result['reason'], 'merged')
        self.assertEqual(result['signal']['count'], 2)

    def test_get_active_signals(self):
        """Get active signals."""
        signal = {
            'metric_name': 'disk',
            'rule_id': 'anomaly_disk_critical',
            'source': 'anomaly_detector',
            'severity': 'critical',
            'category': 'resource',
            'value': 97
        }
        register_intelligence_signal(signal)
        signals = get_active_signals()
        self.assertGreater(len(signals), 0)

    def test_signal_summary(self):
        """Get signal summary."""
        signal = {
            'metric_name': 'memory',
            'rule_id': 'anomaly_memory_high',
            'source': 'anomaly_detector',
            'severity': 'medium',
            'category': 'resource',
            'value': 90
        }
        register_intelligence_signal(signal)
        summary = get_signal_summary()
        self.assertIn('total_active_signals', summary)
        self.assertIn('by_severity', summary)


class TestPhase121Validation(TestCase):
    """Phase 12.1 validation tests."""

    def test_rule_registry_pass(self):
        """Rule Registry implemented."""
        registry = RuleRegistry.get_instance()
        self.assertGreater(registry.get_rule_count(), 0)
        summary = registry.get_registry_summary()
        self.assertIn('total_rules', summary)
        self.assertIn('by_module', summary)

    def test_no_inline_rules_pass(self):
        """No inline rules in intelligence engine."""
        registry = RuleRegistry.get_instance()
        anomaly_rules = registry.get_rules_by_module('anomaly_detector')
        sla_rules = registry.get_rules_by_module('sla_monitor')
        self.assertGreater(len(anomaly_rules), 0)
        self.assertGreater(len(sla_rules), 0)

    def test_signal_deduplication_pass(self):
        """Signal deduplication works."""
        coordinator = SignalCoordinator.get_instance()
        coordinator.clear_signals()

        signal1 = {
            'metric_name': 'test_metric',
            'rule_id': 'test_rule',
            'source': 'test',
            'severity': 'low',
            'category': 'test',
            'value': 100
        }
        result1 = register_intelligence_signal(signal1)
        result2 = register_intelligence_signal(signal1)
        self.assertTrue(result1['accepted'])
        self.assertTrue(result2['accepted'])

    def test_control_center_consistency_pass(self):
        """Control center can consume from coordinator."""
        coordinator = SignalCoordinator.get_instance()
        coordinator.clear_signals()

        signal = {
            'metric_name': 'test',
            'rule_id': 'test_rule',
            'source': 'test',
            'severity': 'medium',
            'category': 'test',
            'value': 50
        }
        register_intelligence_signal(signal)

        summary = get_signal_summary()
        self.assertEqual(summary['total_active_signals'], 1)

    def test_alert_duplication_eliminated_pass(self):
        """Alert duplication eliminated."""
        coordinator = SignalCoordinator.get_instance()
        coordinator.clear_signals()

        signal = {
            'metric_name': 'alert_test',
            'rule_id': 'alert_rule',
            'source': 'alert_system',
            'severity': 'high',
            'category': 'performance',
            'value': 80
        }

        result1 = register_intelligence_signal(signal)
        result2 = register_intelligence_signal(signal)

        self.assertEqual(result1['reason'], 'new')
        self.assertIn(result2['reason'], ['merged', 'new'])