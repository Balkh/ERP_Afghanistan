"""Tests for control center reporting subpackage."""
import unittest

from simulation.control_center.models import (
    AggregatedState,
    ExecutiveReport,
    IncidentRecord,
    IncidentStatus,
    IntelligenceSeverity,
    OperationalPriority,
    OperationalSignal,
    OperationalState,
    SignalType,
)
from simulation.control_center.reporting.executive_summary import ExecutiveSummary
from simulation.control_center.reporting.operational_risk_report import OperationalRiskReport
from simulation.control_center.reporting.intelligence_digest import IntelligenceDigest
from simulation.control_center.reporting.system_stability_report import SystemStabilityReport


def _make_aggregated_state(state_val, severity_score=0.0, critical_count=0, incident_count=0):
    return AggregatedState(
        state=OperationalState(state_val),
        severity_score=severity_score,
        active_signals=critical_count + 1,
        critical_count=critical_count,
        incident_count=incident_count,
        source_summaries={"test": 1},
        priority=OperationalPriority.LOWEST,
    )


def _make_incident(incident_id, severity):
    return IncidentRecord(
        incident_id=incident_id,
        signal_type=SignalType.TRUTH_MISMATCH,
        severity=severity,
        status=IncidentStatus.OPEN,
        tick_detected=1,
        description='test',
    )


def _make_signal(signal_id, signal_type, severity, source_phase='phase3a'):
    return OperationalSignal(
        signal_id=signal_id, signal_type=signal_type, severity=severity,
        source_phase=source_phase, tick=1, description='test',
    )


class TestExecutiveSummary(unittest.TestCase):
    def setUp(self):
        self.summary = ExecutiveSummary(max_reports=5)

    def test_generate_and_retrieve(self):
        report = self.summary.generate_report(
            report_id='rep-1', tick=1, title='Test',
            operational_state='normal', stability_score=95.0,
            summary='Everything ok',
        )
        self.assertIsInstance(report, ExecutiveReport)
        self.assertEqual(report.report_id, 'rep-1')
        self.assertEqual(report.tick, 1)
        self.assertEqual(report.title, 'Test')
        self.assertEqual(report.operational_state, 'normal')
        self.assertEqual(report.stability_score, 95.0)

        retrieved = self.summary.get_report('rep-1')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.report_id, 'rep-1')

    def test_get_latest_report(self):
        self.assertIsNone(self.summary.get_latest_report())
        self.summary.generate_report('r1', 1, 'A', 'normal', 90.0, 's1')
        self.summary.generate_report('r2', 2, 'B', 'normal', 80.0, 's2')
        latest = self.summary.get_latest_report()
        self.assertEqual(latest.report_id, 'r2')

    def test_filter_by_tick_range(self):
        self.summary.generate_report('r1', 1, 'A', 'normal', 90.0, 's1')
        self.summary.generate_report('r2', 2, 'B', 'normal', 80.0, 's2')
        self.summary.generate_report('r3', 3, 'C', 'normal', 70.0, 's3')
        results = self.summary.get_reports(tick_start=2, tick_end=3)
        self.assertEqual(len(results), 2)
        ticks = [r.tick for r in results]
        self.assertIn(2, ticks)
        self.assertIn(3, ticks)

    def test_bounded_by_max_reports(self):
        for i in range(10):
            self.summary.generate_report(f'r{i}', i, f'T{i}', 'normal', 100.0, f's{i}')
        self.assertEqual(self.summary.get_report_count(), 5)
        results = self.summary.get_reports()
        self.assertEqual(len(results), 5)

    def test_sections_and_recommendations(self):
        report = self.summary.generate_report(
            report_id='r1', tick=1, title='Test',
            operational_state='normal', stability_score=90.0,
            summary='test',
            sections={'drilldown': {'key': 'val'}},
            recommendations=['fix it'],
        )
        self.assertEqual(report.sections, {'drilldown': {'key': 'val'}})
        self.assertEqual(report.recommendations, ['fix it'])

    def test_get_report_count_and_clear(self):
        self.assertEqual(self.summary.get_report_count(), 0)
        self.summary.generate_report('r1', 1, 'A', 'normal', 90.0, 's1')
        self.assertEqual(self.summary.get_report_count(), 1)
        self.summary.clear()
        self.assertEqual(self.summary.get_report_count(), 0)
        self.assertIsNone(self.summary.get_report('r1'))


class TestOperationalRiskReport(unittest.TestCase):
    def setUp(self):
        self.risk = OperationalRiskReport(max_reports=10)

    def test_generates_report_from_state_and_incidents(self):
        state = _make_aggregated_state('normal', severity_score=2.0, incident_count=1)
        incidents = [_make_incident('inc-1', IntelligenceSeverity.LOW)]
        report = self.risk.generate_risk_report(
            report_id='risk-1', tick=1, aggregated_state=state,
            incidents=incidents, escalations=[],
        )
        self.assertIsInstance(report, ExecutiveReport)
        self.assertEqual(report.report_id, 'risk-1')
        self.assertEqual(report.tick, 1)
        self.assertIn('Operational Risk Report', report.title)

    def test_risk_report_has_recommendations(self):
        state = _make_aggregated_state('normal', severity_score=2.0, incident_count=1)
        incidents = [_make_incident('inc-1', IntelligenceSeverity.LOW)]
        report = self.risk.generate_risk_report(
            'risk-2', 1, state, incidents, [],
        )
        self.assertGreater(len(report.recommendations), 0)

    def test_critical_state_different_recommendations_than_normal(self):
        normal_state = _make_aggregated_state('normal', severity_score=1.0)
        critical_state = _make_aggregated_state('critical', severity_score=8.0,
                                                 critical_count=3, incident_count=2)
        incidents = [_make_incident('inc-1', IntelligenceSeverity.CRITICAL)]

        normal_report = self.risk.generate_risk_report(
            'norm', 1, normal_state, [], [],
        )
        critical_report = self.risk.generate_risk_report(
            'crit', 2, critical_state, incidents, [],
        )
        critical_recs = ' '.join(critical_report.recommendations).lower()
        self.assertIn('immediate escalation', critical_recs)
        normal_text = ' '.join(normal_report.recommendations).lower()
        self.assertIn('no immediate action', normal_text)

    def test_empty_incidents_still_valid(self):
        state = _make_aggregated_state('normal')
        report = self.risk.generate_risk_report(
            'risk-empty', 1, state, [], [],
        )
        self.assertIsNotNone(report)
        self.assertGreater(len(report.recommendations), 0)

    def test_get_risk_report(self):
        state = _make_aggregated_state('normal')
        self.risk.generate_risk_report('r1', 1, state, [], [])
        retrieved = self.risk.get_risk_report('r1')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.report_id, 'r1')

    def test_risk_report_has_incident_breakdown_section(self):
        incidents = [
            _make_incident('i1', IntelligenceSeverity.HIGH),
            _make_incident('i2', IntelligenceSeverity.LOW),
        ]
        state = _make_aggregated_state('normal')
        report = self.risk.generate_risk_report('r1', 1, state, incidents, [])
        self.assertIn('incident_breakdown', report.sections)
        self.assertIn('top_risks', report.sections)


class TestIntelligenceDigest(unittest.TestCase):
    def setUp(self):
        self.digest = IntelligenceDigest(max_digests=10)

    def test_generates_digest_from_signals_and_incidents(self):
        signals = [_make_signal('s1', SignalType.ANOMALY, IntelligenceSeverity.HIGH)]
        incidents = [_make_incident('i1', IntelligenceSeverity.MEDIUM)]
        report = self.digest.generate_digest(
            digest_id='dig-1', tick=1, signals=signals,
            incidents=incidents, health_data={'operational_state': 'normal', 'stability_score': 90.0},
        )
        self.assertIsInstance(report, ExecutiveReport)
        self.assertEqual(report.report_id, 'dig-1')
        self.assertEqual(report.tick, 1)
        self.assertIn('Intelligence Digest', report.title)

    def test_digest_has_summary_and_recommendations(self):
        signals = [_make_signal('s1', SignalType.INTEGRITY_BREACH, IntelligenceSeverity.CRITICAL)]
        incidents = [_make_incident('i1', IntelligenceSeverity.HIGH)]
        report = self.digest.generate_digest(
            'dig-2', 1, signals, incidents,
            {'operational_state': 'degraded', 'stability_score': 50.0},
        )
        self.assertGreater(len(report.summary), 0)
        self.assertGreater(len(report.recommendations), 0)

    def test_empty_signals_and_incidents(self):
        report = self.digest.generate_digest(
            'dig-empty', 1, [], [],
            {'operational_state': 'normal', 'stability_score': 100.0},
        )
        self.assertIsNotNone(report)
        self.assertEqual(report.sections['signal_summary']['total_signals'], 0)
        self.assertEqual(report.sections['incident_summary']['total_incidents'], 0)
        recs = ' '.join(report.recommendations).lower()
        self.assertIn('no significant issues', recs)

    def test_get_digest(self):
        self.digest.generate_digest(
            'd1', 1, [], [],
            {'operational_state': 'normal', 'stability_score': 100.0},
        )
        retrieved = self.digest.get_digest('d1')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.report_id, 'd1')

    def test_get_latest_digest(self):
        self.assertIsNone(self.digest.get_latest_digest())
        self.digest.generate_digest(
            'd1', 1, [], [],
            {'operational_state': 'normal', 'stability_score': 100.0},
        )
        self.digest.generate_digest(
            'd2', 2, [], [],
            {'operational_state': 'normal', 'stability_score': 90.0},
        )
        latest = self.digest.get_latest_digest()
        self.assertEqual(latest.report_id, 'd2')

    def test_digest_sections(self):
        signals = [
            _make_signal('s1', SignalType.DRIFT_TREND, IntelligenceSeverity.LOW),
            _make_signal('s2', SignalType.TRUTH_MISMATCH, IntelligenceSeverity.HIGH),
        ]
        report = self.digest.generate_digest(
            'd1', 1, signals, [],
            {'operational_state': 'normal', 'stability_score': 95.0},
        )
        self.assertIn('signal_summary', report.sections)
        self.assertIn('health_overview', report.sections)
        self.assertIn('key_findings', report.sections)


class TestSystemStabilityReport(unittest.TestCase):
    def setUp(self):
        self.stability = SystemStabilityReport(max_reports=10)

    def test_generates_report_with_score_and_trend(self):
        report = self.stability.generate_stability_report(
            report_id='stab-1', tick=1, stability_score=85.0,
            health_status='healthy', trend='stable',
            drift_data=[], violation_count=0,
        )
        self.assertIsInstance(report, ExecutiveReport)
        self.assertEqual(report.report_id, 'stab-1')
        self.assertEqual(report.tick, 1)
        self.assertEqual(report.stability_score, 85.0)
        self.assertEqual(report.operational_state, 'healthy')
        self.assertIn('System Stability Report', report.title)

    def test_high_score_healthy_recommend_stable(self):
        report = self.stability.generate_stability_report(
            'r1', 1, 85.0, 'healthy', 'improving', [], 0,
        )
        recs = ' '.join(report.recommendations).lower()
        self.assertIn('stable', recs)

    def test_low_score_critical_recommend_immediate_attention(self):
        report = self.stability.generate_stability_report(
            'r2', 2, 30.0, 'critical', 'degrading', [], 0,
        )
        recs = ' '.join(report.recommendations).lower()
        self.assertIn('immediate', recs)

    def test_violations_included_in_recommendations(self):
        report = self.stability.generate_stability_report(
            'r3', 3, 60.0, 'degraded', 'degrading', [], 5,
        )
        recs = ' '.join(report.recommendations).lower()
        self.assertIn('violation', recs)

    def test_get_stability_report(self):
        self.stability.generate_stability_report(
            'r1', 1, 90.0, 'healthy', 'stable', [], 0,
        )
        retrieved = self.stability.get_stability_report('r1')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.report_id, 'r1')

    def test_bounded_capacity(self):
        for i in range(20):
            self.stability.generate_stability_report(
                f'r{i}', i, 90.0, 'healthy', 'stable', [], 0,
            )
        self.assertEqual(self.stability.get_report_count(), 10)

    def test_stability_report_sections(self):
        drift_data = [{'metric': 'cpu', 'drift': 0.1}]
        report = self.stability.generate_stability_report(
            'r1', 1, 75.0, 'degraded', 'degrading', drift_data, 2,
        )
        self.assertIn('stability_overview', report.sections)
        self.assertIn('trend_analysis', report.sections)
        self.assertIn('drift_summary', report.sections)
        self.assertEqual(report.sections['drift_summary']['total_drift_entries'], 1)

    def test_zero_violation_and_high_score_no_urgent(self):
        report = self.stability.generate_stability_report(
            'r1', 1, 95.0, 'healthy', 'stable', [], 0,
        )
        recs = ' '.join(report.recommendations).lower()
        self.assertIn('no urgent', recs)


if __name__ == '__main__':
    unittest.main()
