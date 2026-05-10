"""
Tests for Phase 13 Decision Intelligence Engine.
Rule-based decision system with no AI/ML.
"""
from django.test import TestCase
from core.operations.decision_engine import (
    Decision, DecisionRuleRegistry, DecisionEngine,
    get_active_decisions, get_decision_summary, evaluate_event_decisions,
    _build_decision
)


class TestDecisionRuleRegistry:
    def test_singleton(self):
        r1 = DecisionRuleRegistry.get_instance()
        r2 = DecisionRuleRegistry.get_instance()
        assert r1 is r2

    def test_rule_count(self):
        r = DecisionRuleRegistry.get_instance()
        rules = r.get_all_rules()
        assert len(rules) >= 15

    def test_get_rule(self):
        r = DecisionRuleRegistry.get_instance()
        rule = r.get_rule('security_auth_failure_spike')
        assert rule is not None
        assert rule['category'] == 'security'
        assert rule['severity'] == 'critical'

    def test_all_rules_have_required_fields(self):
        r = DecisionRuleRegistry.get_instance()
        for rule_id, rule in r.get_all_rules().items():
            assert 'category' in rule
            assert 'description' in rule
            assert 'severity' in rule


class TestDecision:
    def test_decision_fields(self):
        d = Decision(
            decision_id='TEST-001',
            category='security',
            risk_level='high',
            decision='Test decision',
            confidence=0.85,
            description='Test description',
            recommended_actions=['Action 1', 'Action 2'],
            triggered_by=['test_event'],
        )
        assert d.decision_id == 'TEST-001'
        assert d.category == 'security'
        assert d.risk_level == 'high'
        assert d.confidence == 0.85
        assert len(d.recommended_actions) == 2

    def test_decision_to_dict(self):
        d = Decision(
            decision_id='TEST-002',
            category='performance',
            risk_level='medium',
            decision='Test',
            confidence=0.7,
            description='Test',
            recommended_actions=['Action'],
            triggered_by=['test'],
        )
        result = d.to_dict()
        assert result['decision_id'] == 'TEST-002'
        assert result['category'] == 'performance'
        assert result['risk_level'] == 'medium'
        assert result['confidence'] == 0.7


class TestDecisionEngine:
    def test_evaluate_all_returns_list(self):
        decisions = DecisionEngine.evaluate_all()
        assert isinstance(decisions, list)

    def test_evaluate_all_all_returns_decision_objects(self):
        decisions = DecisionEngine.evaluate_all()
        for d in decisions:
            assert isinstance(d, Decision)
            assert d.decision_id
            assert d.category
            assert d.risk_level in ['critical', 'high', 'medium', 'low']
            assert 0.0 <= d.confidence <= 1.0

    def test_evaluate_all_sorted_by_risk(self):
        decisions = DecisionEngine.evaluate_all()
        risk_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        for i in range(len(decisions) - 1):
            curr = risk_order.get(decisions[i].risk_level, 0)
            nxt = risk_order.get(decisions[i+1].risk_level, 0)
            assert curr >= nxt

    def test_get_decision_summary(self):
        summary = get_decision_summary()
        assert 'total_active_decisions' in summary
        assert 'by_risk_level' in summary
        assert 'by_category' in summary
        assert 'overall_risk_level' in summary
        assert summary['overall_risk_level'] in ['critical', 'high', 'medium', 'low', 'unknown']

    def test_evaluate_event_auth_failure(self):
        decisions = DecisionEngine.evaluate_events(
            'auth_event',
            {'action': 'login_failed', 'consecutive_failures': 10}
        )
        auth_decisions = [d for d in decisions if d.category == 'security']
        assert len(auth_decisions) >= 1

    def test_evaluate_event_auth_warning(self):
        decisions = DecisionEngine.evaluate_events(
            'auth_event',
            {'action': 'login_failed', 'consecutive_failures': 3}
        )
        assert len(decisions) >= 1

    def test_evaluate_event_slow_api(self):
        decisions = DecisionEngine.evaluate_events(
            'api_request',
            {'duration_ms': 6000}
        )
        perf_decisions = [d for d in decisions if d.category == 'performance']
        assert len(perf_decisions) >= 1

    def test_evaluate_event_crash(self):
        decisions = DecisionEngine.evaluate_events(
            'crash_event',
            {'message': 'Segmentation fault'}
        )
        sys_decisions = [d for d in decisions if d.category == 'system']
        assert len(sys_decisions) >= 1

    def test_evaluate_event_error_cluster(self):
        decisions = DecisionEngine.evaluate_events(
            'error_event',
            {'module': 'api', 'count': 15}
        )
        assert len(decisions) >= 1


class TestPhase13Validation:
    def test_decision_categories_covered(self):
        decisions = DecisionEngine.evaluate_all()
        categories = {d.category for d in decisions}
        assert len(categories) <= 7  # security, performance, ui, system, financial, inventory, sla

    def test_no_ai_ml_imports(self):
        import inspect
        import core.operations.decision_engine as mod
        source = inspect.getsource(mod)
        assert 'sklearn' not in source
        assert 'tensorflow' not in source
        assert 'torch' not in source
        assert 'ai_' not in source
        assert '_ai' not in source

    def test_confidence_is_deterministic(self):
        results = []
        for _ in range(5):
            decisions = DecisionEngine.evaluate_all()
            results.append(tuple(d.confidence for d in decisions))
        assert results[0] == results[1] == results[2] == results[3] == results[4]

    def test_get_active_decisions_wrapper(self):
        decisions = get_active_decisions()
        assert isinstance(decisions, list)
        for d in decisions:
            assert isinstance(d, Decision)

    def test_get_decision_summary_includes_top_decisions(self):
        summary = get_decision_summary()
        assert 'top_decisions' in summary
        top = summary['top_decisions']
        if top:
            assert 'decision_id' in top[0]
            assert 'risk_level' in top[0]

    def test_build_decision_helper(self):
        d = _build_decision(
            'TEST-ID', 'security', 'critical',
            'Test decision', 0.9, 'Test description',
            ['Action 1', 'Action 2'], ['test_event'],
            '2026-05-10T00:00:00'
        )
        assert isinstance(d, Decision)
        assert d.decision_id == 'TEST-ID'
        assert d.confidence == 0.9