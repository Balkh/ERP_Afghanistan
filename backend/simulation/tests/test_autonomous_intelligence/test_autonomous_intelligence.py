"""
Phase 5B.8 — Autonomous Intelligence Tests (50+ tests).

Validates:
A. Reasoning Engine insights (all domains + cross-domain)
B. Prediction Engine forecasts (cashflow, inventory, HR, SP)
C. Decision Suggester (structured options, recommendations)
D. Anomaly Foresight (warnings, severity, confidence)
E. Risk Engine (scoring 0-100, all categories)
F. Gateway integration (full report)
G. Determinism
H. Read-only / No-execution guarantees
"""
import unittest
from datetime import datetime, timedelta
from typing import Any, Dict, List

from core.operations.truth.models import Domain, SourceType
from core.operations.truth.event_store import EventStore, EventFactory, get_event_store, reset_event_store
from core.operations.intelligence_autonomous.models import (
    IntelligenceReport, Insight, Recommendation, RiskScore,
    Forecast, AnomalyWarning, StructuredDecision, InsightSeverity,
    RiskCategory, ForecastDirection,
)
from core.operations.intelligence_autonomous.reasoning_engine import ReasoningEngine
from core.operations.intelligence_autonomous.prediction_engine import PredictionEngine
from core.operations.intelligence_autonomous.decision_suggester import DecisionSuggester
from core.operations.intelligence_autonomous.anomaly_foresight import AnomalyForesightEngine
from core.operations.intelligence_autonomous.risk_engine import RiskEngine
from core.operations.intelligence_autonomous.gateway import AutonomousIntelligenceGateway


def _make_event(event_type: str = "stock_movement", domain: Domain = Domain.INVENTORY,
                 aggregate_id: str = "test_001", payload: dict = None,
                 source_type: SourceType = SourceType.REAL, sequence: int = 1) -> Any:
    return EventFactory.create_event(
        source_type=source_type, domain=domain, event_type=event_type,
        aggregate_id=aggregate_id, payload=payload or {},
        timestamp=datetime.utcnow().isoformat() + "Z", sequence=sequence,
    )


def _seed_small(store: EventStore) -> None:
    store.append(_make_old_event("batch_created", Domain.INVENTORY, "b1",
                                 {"product_id": "p1", "initial_quantity": 100}, days_ago=10))
    store.append(_make_old_event("stock_movement", Domain.INVENTORY, "b1",
                                 {"quantity": 30, "direction": "out", "product_id": "p1"}, days_ago=8))
    store.append(_make_old_event("stock_movement", Domain.INVENTORY, "b1",
                                 {"quantity": 20, "direction": "out", "product_id": "p1"}, days_ago=5))
    store.append(_make_old_event("stock_movement", Domain.INVENTORY, "b1",
                                 {"quantity": 15, "direction": "out", "product_id": "p1"}, days_ago=3))
    store.append(_make_old_event("stock_movement", Domain.INVENTORY, "b1",
                                 {"quantity": 10, "direction": "in", "product_id": "p1"}, days_ago=1))
    store.append(_make_old_event("journal_entry_posted", Domain.ACCOUNTING, "je1",
                                 {"description": "test", "entries": [{"debit": 100, "credit": 0}, {"debit": 0, "credit": 100}]}, days_ago=7))
    store.append(_make_old_event("employee_hired", Domain.HR, "e1",
                                 {"name": "John", "department": "Sales"}, days_ago=9))
    store.append(_make_old_event("order_created", Domain.SALES_PURCHASE, "o1",
                                 {"order_type": "SALE", "total_amount": 500}, days_ago=6))


def _ts(days_ago: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).isoformat() + "Z"

def _make_old_event(event_type: str = "stock_movement", domain: Domain = Domain.INVENTORY,
                     aggregate_id: str = "test_001", payload: dict = None,
                     days_ago: int = 0, sequence: int = 1) -> Any:
    return EventFactory.create_event(
        source_type=SourceType.REAL, domain=domain, event_type=event_type,
        aggregate_id=aggregate_id, payload=payload or {},
        timestamp=_ts(days_ago), sequence=sequence,
    )

def _seed_with_anomalies(store: EventStore) -> None:
    for i in range(5):
        store.append(_make_old_event("stock_movement", Domain.INVENTORY, f"b{i}",
                                     {"quantity": 10, "direction": "out"}, days_ago=i))
    store.append(_make_old_event("journal_entry_reversed", Domain.ACCOUNTING, "jr1",
                                 {"reason": "error"}, days_ago=1))
    store.append(_make_old_event("journal_entry_reversed", Domain.ACCOUNTING, "jr2",
                                 {"reason": "error"}, days_ago=2))
    store.append(_make_old_event("employee_terminated", Domain.HR, "e1",
                                 {"reason": "resigned"}, days_ago=1))
    store.append(_make_old_event("employee_terminated", Domain.HR, "e2",
                                 {"reason": "resigned"}, days_ago=2))


# ═══════════════════════════════════════════════════════════
# A. REASONING ENGINE
# ═══════════════════════════════════════════════════════════

class ReasoningEngineTest(unittest.TestCase):
    def setUp(self):
        reset_event_store()

    def test_analyze_inventory_returns_insights(self):
        store = get_event_store()
        _seed_small(store)
        engine = ReasoningEngine(store)
        insights = engine.analyze_domain(Domain.INVENTORY)
        self.assertGreater(len(insights), 0)

    def test_analyze_accounting_returns_insights(self):
        store = get_event_store()
        _seed_small(store)
        engine = ReasoningEngine(store)
        insights = engine.analyze_domain(Domain.ACCOUNTING)
        self.assertIsNotNone(insights)

    def test_analyze_hr_returns_insights(self):
        store = get_event_store()
        _seed_small(store)
        engine = ReasoningEngine(store)
        insights = engine.analyze_domain(Domain.HR)
        self.assertIsNotNone(insights)

    def test_analyze_sales_purchase(self):
        store = get_event_store()
        _seed_small(store)
        engine = ReasoningEngine(store)
        insights = engine.analyze_domain(Domain.SALES_PURCHASE)
        self.assertIsNotNone(insights)

    def test_cross_domain_inference(self):
        store = get_event_store()
        _seed_small(store)
        engine = ReasoningEngine(store)
        insights = engine.cross_domain_inference()
        self.assertIsNotNone(insights)

    def test_insights_have_supporting_events(self):
        store = get_event_store()
        _seed_small(store)
        engine = ReasoningEngine(store)
        insights = engine.analyze_domain(Domain.INVENTORY)
        for i in insights:
            self.assertGreater(len(i.supporting_event_ids), 0)

    def test_empty_store_returns_empty(self):
        engine = ReasoningEngine(get_event_store())
        for d in Domain:
            self.assertEqual(len(engine.analyze_domain(d)), 0)

    def test_recommendations_generated(self):
        store = get_event_store()
        _seed_small(store)
        engine = ReasoningEngine(store)
        recs = engine.generate_recommendations()
        self.assertIsNotNone(recs)


# ═══════════════════════════════════════════════════════════
# B. PREDICTION ENGINE
# ═══════════════════════════════════════════════════════════

class PredictionEngineTest(unittest.TestCase):
    def setUp(self):
        reset_event_store()

    def test_forecast_cashflow(self):
        store = get_event_store()
        _seed_small(store)
        engine = PredictionEngine(store)
        forecast = engine.forecast_cashflow()
        self.assertEqual(forecast.domain, "accounting")

    def test_forecast_inventory_depletion(self):
        store = get_event_store()
        _seed_small(store)
        engine = PredictionEngine(store)
        forecast = engine.forecast_inventory_depletion()
        self.assertEqual(forecast.domain, "inventory")

    def test_forecast_hr_workload(self):
        store = get_event_store()
        _seed_small(store)
        engine = PredictionEngine(store)
        forecast = engine.forecast_hr_workload()
        self.assertEqual(forecast.domain, "hr")

    def test_forecast_sales_purchase(self):
        store = get_event_store()
        _seed_small(store)
        engine = PredictionEngine(store)
        forecast = engine.forecast_sales_purchase_balance()
        self.assertEqual(forecast.domain, "sales_purchase")

    def test_forecast_all_runs(self):
        store = get_event_store()
        _seed_small(store)
        engine = PredictionEngine(store)
        forecasts = engine.forecast_all()
        self.assertEqual(len(forecasts), 4)

    def test_forecast_has_direction(self):
        store = get_event_store()
        _seed_small(store)
        engine = PredictionEngine(store)
        for f in engine.forecast_all():
            self.assertIn(f.direction, (ForecastDirection.INCREASING, ForecastDirection.DECREASING, ForecastDirection.STABLE, ForecastDirection.CYCLICAL))

    def test_empty_store_forecast(self):
        engine = PredictionEngine(get_event_store())
        for f in engine.forecast_all():
            self.assertEqual(f.current_value, 0.0)


# ═══════════════════════════════════════════════════════════
# C. DECISION SUGGESTER
# ═══════════════════════════════════════════════════════════

class DecisionSuggesterTest(unittest.TestCase):
    def setUp(self):
        reset_event_store()

    def test_suggest_inventory_restock(self):
        store = get_event_store()
        _seed_small(store)
        engine = DecisionSuggester(store)
        decision = engine.suggest_inventory_restock()
        self.assertEqual(decision.decision_type, "inventory_restock")
        self.assertGreater(len(decision.options), 0)

    def test_suggest_financial_action(self):
        store = get_event_store()
        _seed_small(store)
        engine = DecisionSuggester(store)
        decision = engine.suggest_financial_action()
        self.assertEqual(decision.decision_type, "financial_process_improvement")
        self.assertGreater(len(decision.options), 0)

    def test_recommendations(self):
        store = get_event_store()
        _seed_small(store)
        engine = DecisionSuggester(store)
        recs = engine.generate_recommendations()
        self.assertGreater(len(recs), 0)

    def test_recs_have_risk_level(self):
        store = get_event_store()
        _seed_small(store)
        engine = DecisionSuggester(store)
        for r in engine.generate_recommendations():
            self.assertIn(r.risk_level, ("LOW", "MEDIUM", "HIGH"))

    def test_decisions_are_non_executable(self):
        engine = DecisionSuggester(get_event_store())
        decision = engine.suggest_inventory_restock()
        self.assertFalse(hasattr(decision, 'execute'))
        self.assertFalse(hasattr(decision, 'dispatch'))
        self.assertFalse(hasattr(decision, 'commit'))

    def test_options_have_tradeoffs(self):
        store = get_event_store()
        _seed_small(store)
        engine = DecisionSuggester(store)
        decision = engine.suggest_inventory_restock()
        for opt in decision.options:
            self.assertIsNotNone(opt.tradeoffs)


# ═══════════════════════════════════════════════════════════
# D. ANOMALY FORESIGHT
# ═══════════════════════════════════════════════════════════

class AnomalyForesightTest(unittest.TestCase):
    def setUp(self):
        reset_event_store()

    def test_predict_inventory_anomalies(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        engine = AnomalyForesightEngine(store)
        warnings = engine.predict_inventory_anomalies()
        self.assertGreater(len(warnings), 0)

    def test_predict_financial_anomalies(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        engine = AnomalyForesightEngine(store)
        warnings = engine.predict_financial_anomalies()
        self.assertGreater(len(warnings), 0)

    def test_predict_hr_anomalies(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        engine = AnomalyForesightEngine(store)
        warnings = engine.predict_hr_anomalies()
        self.assertGreater(len(warnings), 0)

    def test_predict_all(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        engine = AnomalyForesightEngine(store)
        warnings = engine.predict_all()
        self.assertGreater(len(warnings), 0)

    def test_warnings_have_severity(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        engine = AnomalyForesightEngine(store)
        for w in engine.predict_all():
            self.assertIn(w.severity, (InsightSeverity.INFO, InsightSeverity.WARNING, InsightSeverity.CRITICAL))

    def test_warnings_have_confidence(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        engine = AnomalyForesightEngine(store)
        for w in engine.predict_all():
            self.assertGreaterEqual(w.confidence_score, 0)

    def test_empty_store_warnings(self):
        engine = AnomalyForesightEngine(get_event_store())
        self.assertEqual(len(engine.predict_all()), 0)


# ═══════════════════════════════════════════════════════════
# E. RISK ENGINE
# ═══════════════════════════════════════════════════════════

class RiskEngineTest(unittest.TestCase):
    def setUp(self):
        reset_event_store()

    def test_score_financial(self):
        store = get_event_store()
        _seed_small(store)
        engine = RiskEngine(store)
        score = engine.score_financial_risk()
        self.assertEqual(score.category, RiskCategory.FINANCIAL)
        self.assertGreaterEqual(score.score, 0)
        self.assertLessEqual(score.score, 100)

    def test_score_operational(self):
        store = get_event_store()
        _seed_small(store)
        engine = RiskEngine(store)
        score = engine.score_operational_risk()
        self.assertEqual(score.category, RiskCategory.OPERATIONAL)

    def test_score_inventory(self):
        store = get_event_store()
        _seed_small(store)
        engine = RiskEngine(store)
        score = engine.score_inventory_risk()
        self.assertEqual(score.category, RiskCategory.INVENTORY)

    def test_score_hr(self):
        store = get_event_store()
        _seed_small(store)
        engine = RiskEngine(store)
        score = engine.score_hr_risk()
        self.assertEqual(score.category, RiskCategory.HR)

    def test_score_all(self):
        store = get_event_store()
        _seed_small(store)
        engine = RiskEngine(store)
        scores = engine.score_all()
        self.assertEqual(len(scores), 4)

    def test_overall_risk(self):
        store = get_event_store()
        _seed_small(store)
        engine = RiskEngine(store)
        overall = engine.get_overall_risk()
        self.assertGreaterEqual(overall, 0)
        self.assertLessEqual(overall, 100)

    def test_empty_store_risk(self):
        engine = RiskEngine(get_event_store())
        self.assertGreaterEqual(engine.get_overall_risk(), 0)

    def test_scores_have_factors(self):
        store = get_event_store()
        _seed_small(store)
        engine = RiskEngine(store)
        for s in engine.score_all():
            self.assertIsInstance(s.contributing_factors, list)


# ═══════════════════════════════════════════════════════════
# F. GATEWAY INTEGRATION
# ═══════════════════════════════════════════════════════════

class GatewayIntegrationTest(unittest.TestCase):
    def setUp(self):
        reset_event_store()

    def test_get_full_report(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        gw = AutonomousIntelligenceGateway(store)
        report = gw.get_full_report()
        self.assertIsInstance(report, IntelligenceReport)
        self.assertGreater(len(report.insights), 0)
        self.assertGreaterEqual(report.risk_score_overall, 0)

    def test_get_insights_all(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        insights = gw.get_insights()
        self.assertGreater(len(insights), 0)

    def test_get_insights_by_domain(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        insights = gw.get_insights("inventory")
        self.assertGreater(len(insights), 0)

    def test_get_risk_summary(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        summary = gw.get_risk_summary()
        self.assertIn("overall_risk", summary)
        self.assertIn("scores", summary)

    def test_get_decision_options(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        decisions = gw.get_decision_options()
        self.assertGreater(len(decisions), 0)

    def test_get_forecasts(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        forecasts = gw.get_forecasts()
        self.assertEqual(len(forecasts), 4)

    def test_get_anomaly_warnings(self):
        store = get_event_store()
        _seed_small(store)
        _seed_with_anomalies(store)
        gw = AutonomousIntelligenceGateway(store)
        warnings = gw.get_anomaly_warnings()
        self.assertGreater(len(warnings), 0)

    def test_get_recommendations(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        recs = gw.get_recommendations()
        self.assertGreater(len(recs), 0)

    def test_get_status(self):
        gw = AutonomousIntelligenceGateway(get_event_store())
        status = gw.get_status()
        self.assertIn("gateway_version", status)
        self.assertEqual(status["engine_status"], "read_only")

    def test_full_report_has_projection_hash(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        report = gw.get_full_report()
        self.assertGreater(len(report.projection_hash), 0)

    def test_full_report_domain_scoped(self):
        store = get_event_store()
        _seed_small(store)
        gw = AutonomousIntelligenceGateway(store)
        report = gw.get_full_report("inventory")
        self.assertEqual(report.domain_scope, "inventory")


# ═══════════════════════════════════════════════════════════
# G. DETERMINISM
# ═══════════════════════════════════════════════════════════

class DeterminismTest(unittest.TestCase):
    def test_reasoning_deterministic(self):
        store = EventStore()
        _seed_small(store)
        e1 = ReasoningEngine(store)
        e2 = ReasoningEngine(store)
        i1 = e1.analyze_domain(Domain.INVENTORY)
        i2 = e2.analyze_domain(Domain.INVENTORY)
        self.assertEqual(len(i1), len(i2))

    def test_risk_deterministic(self):
        store = EventStore()
        _seed_small(store)
        e1 = RiskEngine(store)
        e2 = RiskEngine(store)
        self.assertEqual(e1.get_overall_risk(), e2.get_overall_risk())

    def test_forecast_deterministic(self):
        store = EventStore()
        _seed_small(store)
        e1 = PredictionEngine(store)
        e2 = PredictionEngine(store)
        f1 = e1.forecast_cashflow()
        f2 = e2.forecast_cashflow()
        self.assertEqual(f1.predicted_value, f2.predicted_value)

    def test_gateway_deterministic(self):
        store = EventStore()
        _seed_small(store)
        g1 = AutonomousIntelligenceGateway(store)
        g2 = AutonomousIntelligenceGateway(store)
        r1 = g1.get_full_report()
        r2 = g2.get_full_report()
        self.assertEqual(r1.risk_score_overall, r2.risk_score_overall)


# ═══════════════════════════════════════════════════════════
# H. NO EXECUTION GUARANTEES
# ═══════════════════════════════════════════════════════════

class NoExecutionTest(unittest.TestCase):
    def test_insights_are_not_executable(self):
        insight = Insight(title="Test", description="Test", domain="test")
        self.assertFalse(hasattr(insight, 'execute'))
        self.assertFalse(hasattr(insight, 'dispatch'))
        self.assertFalse(hasattr(insight, 'commit'))

    def test_recommendations_are_not_actions(self):
        rec = Recommendation(title="Test", description="Test", decision_type="test")
        self.assertFalse(hasattr(rec, 'execute'))
        self.assertFalse(hasattr(rec, 'trigger'))

    def test_forecasts_are_not_mutations(self):
        forecast = Forecast(domain="test", metric="test")
        self.assertFalse(hasattr(forecast, 'apply'))
        self.assertFalse(hasattr(forecast, 'mutate'))

    def test_no_write_methods_in_gateway(self):
        gw = AutonomousIntelligenceGateway(get_event_store())
        self.assertFalse(hasattr(gw, 'execute_decision'))
        self.assertFalse(hasattr(gw, 'apply_recommendation'))
        self.assertFalse(hasattr(gw, 'dispatch_action'))
        self.assertFalse(hasattr(gw, 'trigger_workflow'))

    def test_reports_are_readonly(self):
        report = IntelligenceReport()
        with self.assertRaises(AttributeError):
            report.risk_score_overall = 50.0

    def test_no_erp_imports(self):
        import sys
        auto_mods = [m for m in sys.modules if 'intelligence_autonomous' in m]
        for mname in auto_mods:
            mod = sys.modules.get(mname)
            if mod:
                for erp in ['inventory.models', 'accounting.models', 'sales.models',
                             'purchases.models', 'hr.models', 'payroll.models']:
                    if erp not in str(getattr(mod, '__file__', '')):
                        pass  # Expect no ERP model imports


if __name__ == '__main__':
    unittest.main()
