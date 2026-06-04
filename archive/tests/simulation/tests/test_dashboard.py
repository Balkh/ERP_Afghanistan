"""
Tests for Phase 4C Control Center — Dashboard Subpackage.
Fully deterministic. No randomness. No ERP mutation.
"""
import unittest

from simulation.control_center.models import (
    OperationalSignal,
    AggregatedState,
    IncidentRecord,
    IncidentStatus,
    IntelligenceSeverity,
    SignalType,
    OperationalState,
    OperationalPriority,
)
from simulation.control_center.dashboard.dashboard_models import (
    DashboardModelFactory,
)
from simulation.control_center.dashboard.stability_widgets import StabilityWidgets
from simulation.control_center.dashboard.health_summary import HealthSummary
from simulation.control_center.dashboard.operational_heatmap import (
    OperationalHeatmap,
)
from simulation.control_center.dashboard.drift_visualization import (
    DriftVisualization,
)


class TestDashboardModelFactory(unittest.TestCase):
    def setUp(self):
        self.factory = DashboardModelFactory(max_snapshots=5)

    def test_create_and_retrieve_snapshot(self):
        snapshot = self.factory.create_snapshot(
            snapshot_id='snap-001',
            tick=100,
            operational_state='normal',
            stability_score=0.95,
            health_status='healthy',
            active_incidents=0,
            widget_data={'widget_a': 42},
            summary='All systems nominal',
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.snapshot_id, 'snap-001')
        self.assertEqual(snapshot.tick, 100)
        self.assertEqual(snapshot.operational_state, 'normal')
        self.assertEqual(snapshot.stability_score, 0.95)
        self.assertEqual(snapshot.health_status, 'healthy')
        self.assertEqual(snapshot.active_incidents, 0)
        self.assertEqual(snapshot.widget_data, {'widget_a': 42})
        self.assertEqual(snapshot.summary, 'All systems nominal')

        retrieved = self.factory.get_snapshot('snap-001')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.snapshot_id, 'snap-001')

    def test_get_snapshot_nonexistent_returns_none(self):
        self.assertIsNone(self.factory.get_snapshot('nonexistent'))

    def test_get_latest_snapshot(self):
        self.factory.create_snapshot(
            'snap-001', 100, 'normal', 0.95, 'healthy', 0
        )
        self.factory.create_snapshot(
            'snap-002', 101, 'degraded', 0.65, 'degraded', 3
        )
        latest = self.factory.get_latest_snapshot()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.snapshot_id, 'snap-002')
        self.assertEqual(latest.tick, 101)

    def test_get_latest_snapshot_empty_returns_none(self):
        factory = DashboardModelFactory(max_snapshots=5)
        self.assertIsNone(factory.get_latest_snapshot())

    def test_get_snapshots_filters_by_tick_range(self):
        for i in range(10):
            self.factory.create_snapshot(
                f'snap-{i:03d}', 100 + i, 'normal', 0.9, 'healthy', 0
            )
        result = self.factory.get_snapshots(tick_start=103, tick_end=106)
        ticks = [s.tick for s in result]
        self.assertTrue(all(103 <= t <= 106 for t in ticks))

    def test_get_snapshots_newest_first(self):
        for i in range(3):
            self.factory.create_snapshot(
                f'snap-{i:03d}', 100 + i, 'normal', 0.9, 'healthy', 0
            )
        result = self.factory.get_snapshots()
        self.assertEqual(len(result), 3)
        self.assertGreater(result[0].tick, result[-1].tick)

    def test_get_snapshots_respects_limit(self):
        for i in range(10):
            self.factory.create_snapshot(
                f'snap-{i:03d}', 100 + i, 'normal', 0.9, 'healthy', 0
            )
        result = self.factory.get_snapshots(limit=3)
        self.assertEqual(len(result), 3)

    def test_bounded_by_max_snapshots(self):
        for i in range(10):
            self.factory.create_snapshot(
                f'snap-{i:03d}', 100 + i, 'normal', 0.9, 'healthy', 0
            )
        self.assertEqual(self.factory.get_snapshot_count(), 5)
        self.assertIsNone(self.factory.get_snapshot('snap-000'))

    def test_get_snapshot_count(self):
        self.assertEqual(self.factory.get_snapshot_count(), 0)
        self.factory.create_snapshot(
            'snap-001', 100, 'normal', 0.9, 'healthy', 0
        )
        self.assertEqual(self.factory.get_snapshot_count(), 1)

    def test_clear(self):
        self.factory.create_snapshot(
            'snap-001', 100, 'normal', 0.9, 'healthy', 0
        )
        self.factory.clear()
        self.assertEqual(self.factory.get_snapshot_count(), 0)
        self.assertIsNone(self.factory.get_snapshot('snap-001'))

    def test_create_snapshot_clamps_stability_score(self):
        snapshot = self.factory.create_snapshot(
            'snap-001', 100, 'normal', 1.5, 'healthy', 0
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.stability_score, 1.0)

        snapshot2 = self.factory.create_snapshot(
            'snap-002', 101, 'normal', -0.5, 'healthy', 0
        )
        self.assertIsNotNone(snapshot2)
        self.assertEqual(snapshot2.stability_score, 0.0)

    def test_create_snapshot_clamps_active_incidents(self):
        snapshot = self.factory.create_snapshot(
            'snap-001', 100, 'normal', 0.9, 'healthy', -5
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.active_incidents, 0)

    def test_create_snapshot_without_widget_data(self):
        snapshot = self.factory.create_snapshot(
            'snap-001', 100, 'normal', 0.9, 'healthy', 0
        )
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.widget_data, {})

    def test_get_snapshots_no_filters_returns_all(self):
        for i in range(3):
            self.factory.create_snapshot(
                f'snap-{i:03d}', 100 + i, 'normal', 0.9, 'healthy', 0
            )
        result = self.factory.get_snapshots()
        self.assertEqual(len(result), 3)

    def test_get_snapshots_without_start(self):
        for i in range(5):
            self.factory.create_snapshot(
                f'snap-{i:03d}', 100 + i, 'normal', 0.9, 'healthy', 0
            )
        result = self.factory.get_snapshots(tick_end=102)
        for s in result:
            self.assertLessEqual(s.tick, 102)

    def test_get_snapshots_without_end(self):
        for i in range(5):
            self.factory.create_snapshot(
                f'snap-{i:03d}', 100 + i, 'normal', 0.9, 'healthy', 0
            )
        result = self.factory.get_snapshots(tick_start=102)
        for s in result:
            self.assertGreaterEqual(s.tick, 102)


class TestStabilityWidgets(unittest.TestCase):
    def setUp(self):
        self.widgets = StabilityWidgets(max_history=20)

    def test_perfect_score_returns_stable(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.0,
            critical_count=0,
            incident_count=0,
            active_signals=0,
            cascading_risk=False,
        )
        self.assertEqual(result['stability_score'], 1.0)
        self.assertEqual(result['status'], 'stable')

    def test_high_severity_lowers_score(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.8,
            critical_count=0,
            incident_count=0,
            active_signals=0,
            cascading_risk=False,
        )
        self.assertLess(result['stability_score'], 0.5)

    def test_cascading_risk_applies_penalty(self):
        without_cascade = self.widgets.compute_stability_score(
            severity_score=0.0,
            critical_count=0,
            incident_count=0,
            active_signals=0,
            cascading_risk=False,
        )
        with_cascade = self.widgets.compute_stability_score(
            severity_score=0.0,
            critical_count=0,
            incident_count=0,
            active_signals=0,
            cascading_risk=True,
        )
        self.assertEqual(without_cascade['stability_score'], 1.0)
        self.assertEqual(with_cascade['stability_score'], 0.8)

    def test_score_clamped_to_zero(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.5,
            critical_count=10,
            incident_count=10,
            active_signals=0,
            cascading_risk=True,
        )
        self.assertEqual(result['stability_score'], 0.0)

    def test_score_clamped_to_one(self):
        result = self.widgets.compute_stability_score(
            severity_score=-0.5,
            critical_count=0,
            incident_count=0,
            active_signals=0,
            cascading_risk=False,
        )
        self.assertEqual(result['stability_score'], 1.0)

    def test_critical_penalty_applied(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.0,
            critical_count=3,
            incident_count=0,
            active_signals=0,
            cascading_risk=False,
        )
        self.assertEqual(result['stability_score'], 0.7)

    def test_incident_penalty_applied(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.0,
            critical_count=0,
            incident_count=4,
            active_signals=0,
            cascading_risk=False,
        )
        self.assertEqual(result['stability_score'], 0.8)

    def test_breakdown_contains_all_keys(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.3,
            critical_count=1,
            incident_count=2,
            active_signals=5,
            cascading_risk=True,
        )
        breakdown = result['breakdown']
        self.assertIn('base_score', breakdown)
        self.assertIn('severity_score', breakdown)
        self.assertIn('critical_penalty', breakdown)
        self.assertIn('incident_penalty', breakdown)
        self.assertIn('cascading_penalty', breakdown)
        self.assertIn('raw_score', breakdown)
        self.assertIn('cascading_risk', breakdown)

    def test_trend_improving(self):
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        low = self.widgets.compute_stability_score(0.5, 5, 5, 0, True)
        high = self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.assertGreater(high['stability_score'], low['stability_score'])
        trend = self.widgets.get_stability_trend()
        self.assertIn(trend, ('improving', 'stable'))

    def test_trend_degrading(self):
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.compute_stability_score(0.8, 5, 5, 0, True)
        trend = self.widgets.get_stability_trend()
        self.assertEqual(trend, 'degrading')

    def test_trend_empty_history_returns_stable(self):
        widgets = StabilityWidgets(max_history=20)
        self.assertEqual(widgets.get_stability_trend(), 'stable')

    def test_trend_single_entry_returns_stable(self):
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.assertEqual(self.widgets.get_stability_trend(), 'stable')

    def test_clear_resets_history(self):
        self.widgets.compute_stability_score(0.0, 0, 0, 0, False)
        self.widgets.clear()
        self.assertEqual(self.widgets.get_stability_trend(), 'stable')

    def test_status_critical_when_score_below_04(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.5,
            critical_count=5,
            incident_count=5,
            active_signals=0,
            cascading_risk=True,
        )
        self.assertLess(result['stability_score'], 0.4)
        self.assertEqual(result['status'], 'critical')

    def test_status_unstable_when_score_between_04_and_07(self):
        result = self.widgets.compute_stability_score(
            severity_score=0.0,
            critical_count=3,
            incident_count=2,
            active_signals=0,
            cascading_risk=False,
        )
        score = result['stability_score']
        self.assertGreaterEqual(score, 0.4)
        self.assertLess(score, 0.7)
        self.assertEqual(result['status'], 'unstable')


class TestHealthSummary(unittest.TestCase):
    def setUp(self):
        self.summary = HealthSummary(max_summaries=10)

    def test_generates_summary_text_containing_status(self):
        result = self.summary.generate_summary(
            health_status='healthy',
            health_score=0.95,
            operational_state='normal',
            active_signals=0,
            active_incidents=0,
            sources_monitored=5,
        )
        self.assertIn('healthy', result['summary_text'].lower())
        self.assertEqual(result['health_label'], 'healthy')
        self.assertEqual(result['status_icon'], 'check')

    def test_healthy_state_with_incidents(self):
        result = self.summary.generate_summary(
            health_status='healthy',
            health_score=0.9,
            operational_state='normal',
            active_signals=2,
            active_incidents=1,
            sources_monitored=5,
        )
        self.assertIn('healthy', result['summary_text'].lower())
        self.assertIn('2', result['summary_text'])
        self.assertIn('1', result['summary_text'])

    def test_degraded_state_appropriate_label(self):
        result = self.summary.generate_summary(
            health_status='degraded',
            health_score=0.6,
            operational_state='degraded',
            active_signals=3,
            active_incidents=2,
            sources_monitored=5,
        )
        self.assertEqual(result['health_label'], 'degraded')
        self.assertEqual(result['status_icon'], 'warning')

    def test_critical_state(self):
        result = self.summary.generate_summary(
            health_status='critical',
            health_score=0.2,
            operational_state='critical',
            active_signals=5,
            active_incidents=3,
            sources_monitored=5,
        )
        self.assertEqual(result['health_label'], 'critical')
        self.assertEqual(result['status_icon'], 'error')

    def test_emergency_operational_state_triggers_critical(self):
        result = self.summary.generate_summary(
            health_status='healthy',
            health_score=0.9,
            operational_state='emergency',
            active_signals=0,
            active_incidents=0,
            sources_monitored=5,
        )
        self.assertEqual(result['health_label'], 'critical')

    def test_low_score_triggers_critical(self):
        result = self.summary.generate_summary(
            health_status='unknown',
            health_score=0.2,
            operational_state='recovering',
            active_signals=5,
            active_incidents=3,
            sources_monitored=5,
        )
        self.assertEqual(result['health_label'], 'critical')

    def test_history_tracking(self):
        self.summary.generate_summary(
            'healthy', 0.9, 'normal', 0, 0, 3
        )
        self.summary.generate_summary(
            'degraded', 0.6, 'degraded', 2, 1, 3
        )
        history = self.summary.get_summary_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['health_label'], 'healthy')
        self.assertEqual(history[1]['health_label'], 'degraded')

    def test_metrics_contains_sources_and_signals(self):
        result = self.summary.generate_summary(
            'healthy', 0.95, 'normal', 2, 1, 5
        )
        metrics = result['metrics']
        self.assertEqual(metrics['health_score'], 0.95)
        self.assertEqual(metrics['health_score_percent'], 95.0)
        self.assertEqual(metrics['active_signals'], 2)
        self.assertEqual(metrics['active_incidents'], 1)
        self.assertEqual(metrics['sources_monitored'], 5)
        self.assertEqual(metrics['signals_per_source'], 0.4)

    def test_empty_history(self):
        self.assertEqual(self.summary.get_summary_history(), [])

    def test_clear_history(self):
        self.summary.generate_summary(
            'healthy', 0.9, 'normal', 0, 0, 3
        )
        self.summary.clear()
        self.assertEqual(self.summary.get_summary_history(), [])


class TestOperationalHeatmap(unittest.TestCase):
    def setUp(self):
        self.heatmap = OperationalHeatmap(max_cells=100)

    def _make_signal(self, source, severity):
        return OperationalSignal(
            signal_id=f'sig_{source}_{severity}',
            signal_type=SignalType.TRUTH_MISMATCH,
            severity=severity,
            source_phase=source,
            tick=100,
            description='test',
        )

    def test_empty_signals_returns_zeroed_grid(self):
        result = self.heatmap.build_heatmap([])
        self.assertEqual(result['total_signals'], 0)
        self.assertEqual(result['unique_sources'], 0)
        self.assertEqual(result['unique_severities'], 5)
        self.assertEqual(len(result['grid']), 0)

    def test_counts_correctly_by_source_and_severity(self):
        signals = [
            self._make_signal('phase_a', IntelligenceSeverity.CRITICAL),
            self._make_signal('phase_a', IntelligenceSeverity.CRITICAL),
            self._make_signal('phase_a', IntelligenceSeverity.INFO),
            self._make_signal('phase_b', IntelligenceSeverity.HIGH),
        ]
        result = self.heatmap.build_heatmap(signals)
        self.assertEqual(result['total_signals'], 4)
        self.assertEqual(result['unique_sources'], 2)

        grid = result['grid']
        critical_cells = [
            c for c in grid
            if c['source'] == 'phase_a' and c['severity'] == 'critical'
        ]
        self.assertEqual(len(critical_cells), 1)
        self.assertEqual(critical_cells[0]['count'], 2)

    def test_filtering_by_sources(self):
        signals = [
            self._make_signal('phase_a', IntelligenceSeverity.CRITICAL),
            self._make_signal('phase_b', IntelligenceSeverity.HIGH),
            self._make_signal('phase_c', IntelligenceSeverity.INFO),
        ]
        result = self.heatmap.build_heatmap(
            signals, sources=['phase_a', 'phase_b']
        )
        self.assertEqual(result['total_signals'], 2)
        self.assertEqual(result['unique_sources'], 2)
        for cell in result['grid']:
            self.assertIn(cell['source'], ('phase_a', 'phase_b'))

    def test_filtering_by_severities(self):
        signals = [
            self._make_signal('phase_a', IntelligenceSeverity.CRITICAL),
            self._make_signal('phase_a', IntelligenceSeverity.HIGH),
            self._make_signal('phase_a', IntelligenceSeverity.INFO),
        ]
        result = self.heatmap.build_heatmap(
            signals, severities=['critical', 'high']
        )
        self.assertEqual(result['total_signals'], 2)
        for cell in result['grid']:
            if cell['count'] > 0:
                self.assertIn(cell['severity'], ('critical', 'high'))

    def test_exception_safety_bad_signal_data(self):
        signals = [
            None,
            'not_a_signal',
            42,
        ]
        result = self.heatmap.build_heatmap(signals)
        self.assertEqual(result['total_signals'], 0)

    def test_signals_per_source_zero(self):
        result = self.heatmap.build_heatmap([])
        self.assertEqual(result['total_signals'], 0)

    def test_all_severities_auto_detected(self):
        signals = [
            self._make_signal('phase_a', IntelligenceSeverity.CRITICAL),
            self._make_signal('phase_a', IntelligenceSeverity.LOW),
        ]
        result = self.heatmap.build_heatmap(signals)
        self.assertEqual(result['unique_severities'], 5)

    def test_grid_contains_zero_count_cells(self):
        signals = [
            self._make_signal('phase_a', IntelligenceSeverity.CRITICAL),
        ]
        result = self.heatmap.build_heatmap(
            signals, severities=['critical', 'info']
        )
        grid = result['grid']
        info_cells = [c for c in grid if c['severity'] == 'info']
        self.assertTrue(all(c['count'] == 0 for c in info_cells))


class TestDriftVisualization(unittest.TestCase):
    def setUp(self):
        self.drift = DriftVisualization(max_data_points=20)

    def test_record_and_count_drift_points(self):
        point = self.drift.record_drift_point(
            tick=100,
            drift_type='inventory',
            severity='high',
            value=0.75,
            source='warehouse_a',
        )
        self.assertEqual(point['tick'], 100)
        self.assertEqual(point['drift_type'], 'inventory')
        self.assertEqual(point['severity'], 'high')
        self.assertEqual(point['value'], 0.75)
        self.assertEqual(point['source'], 'warehouse_a')
        self.assertEqual(self.drift.get_drift_data_point_count(), 1)

    def test_build_drift_series_all(self):
        self.drift.record_drift_point(100, 'inventory', 'high', 0.75, 'wh_a')
        self.drift.record_drift_point(101, 'financial', 'low', 0.25, 'fin_a')
        result = self.drift.build_drift_series()
        self.assertEqual(result['data_points'], 2)
        self.assertEqual(len(result['series']), 2)

    def test_build_drift_series_filters_by_type(self):
        self.drift.record_drift_point(100, 'inventory', 'high', 0.75, 'wh_a')
        self.drift.record_drift_point(101, 'financial', 'low', 0.25, 'fin_a')
        self.drift.record_drift_point(102, 'inventory', 'medium', 0.5, 'wh_b')
        result = self.drift.build_drift_series(drift_type='inventory')
        self.assertEqual(result['data_points'], 2)
        for p in result['series']:
            self.assertIn(p['tick'], (100, 102))

    def test_build_drift_series_filters_by_source(self):
        self.drift.record_drift_point(100, 'inventory', 'high', 0.75, 'wh_a')
        self.drift.record_drift_point(101, 'inventory', 'low', 0.25, 'wh_b')
        result = self.drift.build_drift_series(source='wh_a')
        self.assertEqual(result['data_points'], 1)
        self.assertEqual(result['series'][0]['tick'], 100)

    def test_build_drift_series_sorted_by_tick(self):
        self.drift.record_drift_point(200, 'latency', 'high', 0.9, 'sys')
        self.drift.record_drift_point(100, 'latency', 'low', 0.1, 'sys')
        result = self.drift.build_drift_series()
        ticks = [p['tick'] for p in result['series']]
        self.assertEqual(ticks, sorted(ticks))

    def test_bounded_by_max_data_points(self):
        for i in range(30):
            self.drift.record_drift_point(i, 'inventory', 'low', 0.1, 'test')
        self.assertEqual(self.drift.get_drift_data_point_count(), 20)

    def test_clear(self):
        self.drift.record_drift_point(100, 'inventory', 'high', 0.75, 'wh_a')
        self.drift.clear()
        self.assertEqual(self.drift.get_drift_data_point_count(), 0)
        result = self.drift.build_drift_series()
        self.assertEqual(result['data_points'], 0)

    def test_build_drift_series_limit(self):
        for i in range(50):
            self.drift.record_drift_point(i, 'inventory', 'low', 0.1, 'test')
        result = self.drift.build_drift_series(limit=5)
        self.assertLessEqual(result['data_points'], 5)

    def test_record_without_source(self):
        point = self.drift.record_drift_point(100, 'inventory', 'high', 0.75)
        self.assertEqual(point['source'], '')

    def test_get_drift_data_point_count_empty(self):
        drift = DriftVisualization(max_data_points=20)
        self.assertEqual(drift.get_drift_data_point_count(), 0)

    def test_build_drift_series_returns_metadata(self):
        self.drift.record_drift_point(100, 'inventory', 'high', 0.75, 'wh_a')
        result = self.drift.build_drift_series()
        self.assertIn('series', result)
        self.assertIn('type', result)
        self.assertIn('source', result)
        self.assertIn('data_points', result)
        self.assertEqual(result['type'], 'all')
        self.assertEqual(result['source'], 'all')


if __name__ == '__main__':
    unittest.main()
