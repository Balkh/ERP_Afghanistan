"""Recovery orchestrator — top-level orchestrator for the entire recovery layer."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import (IntegrityIncident, IntegritySeverity, CorruptionType,
                                        FullRecoveryReport, OperationalStatus, DegradationLevel,
                                        BlastRadiusResult, ContainmentResult, EscalationRecord)
from simulation.recovery.containment.containment_engine import ContainmentEngine
from simulation.recovery.rollback.rollback_simulator import RollbackSimulator
from simulation.recovery.rollback.rollback_risk_analyzer import RollbackRiskAnalyzer
from simulation.recovery.rollback.dependency_rollback_map import DependencyRollbackMap
from simulation.recovery.rollback.rollback_validator import RollbackValidator
from simulation.recovery.escalation.escalation_engine import EscalationEngine
from simulation.recovery.integrity.integrity_guard import IntegrityGuard
from simulation.recovery.integrity.corruption_detector import CorruptionDetector
from simulation.recovery.integrity.partial_state_detector import PartialStateDetector
from simulation.recovery.integrity.consistency_verifier import ConsistencyVerifier
from simulation.recovery.recommendations.recovery_recommender import RecoveryRecommender
from simulation.recovery.blast_radius.blast_radius_engine import BlastRadiusEngine
from simulation.recovery.blast_radius.dependency_impact_map import DependencyImpactMap
from simulation.recovery.blast_radius.financial_risk_estimator import FinancialRiskEstimator
from simulation.recovery.blast_radius.inventory_risk_estimator import InventoryRiskEstimator
from simulation.recovery.degradation.graceful_degradation import GracefulDegradation
from simulation.recovery.orchestration.containment_router import ContainmentRouter
from simulation.recovery.execution.execution_engine import RecoveryExecutionEngine
from simulation.recovery.execution.partial_rollback import PartialRollbackEngine
from simulation.recovery.execution.external_rollback import ExternalRollbackEngine
from simulation.recovery.execution.user_override import UserOverrideHandler


class RecoveryOrchestrator:
    def __init__(self, max_history: int = 500):
        self._containment = ContainmentEngine()
        self._rollback_simulator = RollbackSimulator()
        self._rollback_risk = RollbackRiskAnalyzer()
        self._dependency_map = DependencyRollbackMap()
        self._rollback_validator = RollbackValidator()
        self._escalation = EscalationEngine()
        self._integrity_guard = IntegrityGuard()
        self._corruption_detector = CorruptionDetector()
        self._partial_state = PartialStateDetector()
        self._consistency = ConsistencyVerifier()
        self._recommender = RecoveryRecommender()
        self._blast_radius = BlastRadiusEngine()
        self._dependency_impact = DependencyImpactMap()
        self._financial_risk = FinancialRiskEstimator()
        self._inventory_risk = InventoryRiskEstimator()
        self._degradation = GracefulDegradation()
        self._router = ContainmentRouter()
        self._execution_engine = RecoveryExecutionEngine(max_history=200)
        self._partial_rollback = PartialRollbackEngine(max_history=200)
        self._external_rollback = ExternalRollbackEngine(max_history=200)
        self._user_override = UserOverrideHandler(max_history=200)
        self._incidents: deque = deque(maxlen=max_history)
        self._incident_count: int = 0
        self._current_tick: int = 0

    @property
    def containment(self) -> ContainmentEngine:
        return self._containment

    @property
    def rollback_simulator(self) -> RollbackSimulator:
        return self._rollback_simulator

    @property
    def rollback_risk(self) -> RollbackRiskAnalyzer:
        return self._rollback_risk

    @property
    def dependency_map(self) -> DependencyRollbackMap:
        return self._dependency_map

    @property
    def rollback_validator(self) -> RollbackValidator:
        return self._rollback_validator

    @property
    def escalation(self) -> EscalationEngine:
        return self._escalation

    @property
    def integrity_guard(self) -> IntegrityGuard:
        return self._integrity_guard

    @property
    def corruption_detector(self) -> CorruptionDetector:
        return self._corruption_detector

    @property
    def partial_state(self) -> PartialStateDetector:
        return self._partial_state

    @property
    def consistency(self) -> ConsistencyVerifier:
        return self._consistency

    @property
    def recommender(self) -> RecoveryRecommender:
        return self._recommender

    @property
    def blast_radius(self) -> BlastRadiusEngine:
        return self._blast_radius

    @property
    def dependency_impact(self) -> DependencyImpactMap:
        return self._dependency_impact

    @property
    def financial_risk(self) -> FinancialRiskEstimator:
        return self._financial_risk

    @property
    def inventory_risk(self) -> InventoryRiskEstimator:
        return self._inventory_risk

    @property
    def degradation(self) -> GracefulDegradation:
        return self._degradation

    @property
    def router(self) -> ContainmentRouter:
        return self._router

    @property
    def execution_engine(self) -> RecoveryExecutionEngine:
        return self._execution_engine

    @property
    def partial_rollback(self) -> PartialRollbackEngine:
        return self._partial_rollback

    @property
    def external_rollback(self) -> ExternalRollbackEngine:
        return self._external_rollback

    @property
    def user_override(self) -> UserOverrideHandler:
        return self._user_override

    def execute_recovery(self, containment_result: Dict, approval: Dict, tick: int) -> Dict:
        return self._execution_engine.execute(containment_result, approval, tick)

    def perform_partial_rollback(self, incident: Dict, state: Dict, rollback_map: Dict) -> Dict:
        segment = self._partial_rollback.detect_affected(incident, state)
        rollback_result = self._partial_rollback.execute_rollback(segment, rollback_map)
        merge_result = self._partial_rollback.merge_clean(segment, state)
        verify_result = self._partial_rollback.verify(segment)
        return {
            'detect_affected': segment,
            'execute_rollback': rollback_result,
            'merge_clean': merge_result,
            'verify': verify_result,
        }

    def handle_external_rollback(self, system: str, operation: str, failure: Dict, params: Dict) -> Dict:
        sync_check_result = self._external_rollback.sync_check(system, failure)
        compensate_result = self._external_rollback.compensate(system, operation, failure)
        retry_result = self._external_rollback.retry_with_policy(system, operation, params)
        validate_result = self._external_rollback.validate(system, operation)
        return {
            'sync_check': sync_check_result,
            'compensate': compensate_result,
            'retry_with_policy': retry_result,
            'validate': validate_result,
        }

    def process_user_override(self, request: Dict) -> Dict:
        validate_result = self._user_override.validate(request)
        risk_result = self._user_override.score_risk(request)
        lock_result = self._user_override.audit_lock(request)
        execute_result = self._user_override.controlled_execute(request, risk_result)
        return {
            'validate': validate_result,
            'score_risk': risk_result,
            'audit_lock': lock_result,
            'controlled_execute': execute_result,
        }

    def process_incident(self, corruption_type: CorruptionType,
                         severity: IntegritySeverity,
                         source_module: str, description: str,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        self._incident_count += 1
        incident_id = f"inc_{self._incident_count}"
        tick = context.get('tick', self._current_tick)
        violation = self._integrity_guard.record_violation(
            corruption_type, severity, source_module, description, tick)
        routing = self._router.route(corruption_type, severity, {
            **context, 'workflow_id': context.get('workflow_id', incident_id),
            'source_module': source_module, 'tick': tick,
            'reason': description,
        }, self._containment, self._escalation)
        blast = self._blast_radius.analyze(
            {'estimated_blast_radius': context.get('blast_radius', 0)},
            affected_workflows=context.get('affected_workflows', []),
            affected_modules=[source_module],
        )
        recommendations = self._recommender.generate_recommendations(
            corruption_type, severity,
            blast_radius_score=blast['estimated_impact_score'],
            has_irreversible=context.get('has_irreversible', False),
            workflows_blocked=len(context.get('affected_workflows', [])),
        )
        self._degradation.degrade(
            severity,
            has_irreversible=context.get('has_irreversible', False),
            containment_active=bool(routing.get('actions')),
            reason=f"Incident {incident_id}: {description}",
        )
        incident = IntegrityIncident(
            incident_id=incident_id, severity=severity,
            detected_at_tick=tick,
            blast_radius=BlastRadiusResult(**{k: v for k, v in blast.items()
                                               if k in BlastRadiusResult.__dataclass_fields__}),
            requires_manual_intervention=severity in (IntegritySeverity.HIGH, IntegritySeverity.CRITICAL),
        )
        self._incidents.append(incident)
        return {
            'incident_id': incident_id, 'severity': severity.value,
            'violation': violation, 'routing': routing,
            'blast_radius': blast, 'recommendations': recommendations,
        }

    def generate_recovery_report(self, tick: int) -> Dict[str, Any]:
        self._current_tick = tick
        active_incidents = list(self._incidents)
        containment_report = self._containment.get_containment_report()
        degradation_status = self._degradation.get_current_status()
        overall_risk = self._calculate_overall_risk(active_incidents, containment_report)
        status = self._determine_status(overall_risk, containment_report)
        report = FullRecoveryReport(
            report_id=f"rpt_{tick}", generated_at_tick=tick,
            operational_status=status,
            degradation_level=DegradationLevel(degradation_status['current_level']),
            overall_risk_score=overall_risk,
            recommendations_count=len(active_incidents),
        )
        return {
            'report_id': report.report_id, 'tick': tick,
            'operational_status': status.value,
            'degradation_level': degradation_status['current_level'],
            'overall_risk_score': overall_risk,
            'active_incidents': len(active_incidents),
            'containment': containment_report,
            'degradation': degradation_status,
            'recommendations_count': report.recommendations_count,
        }

    def _calculate_overall_risk(self, incidents: List, containment: Dict[str, Any]) -> float:
        if not incidents:
            return 0.0
        severity_scores = {'critical': 100, 'high': 70, 'medium': 40, 'low': 15, 'info': 0}
        scores = []
        for inc in incidents:
            score = severity_scores.get(inc.severity.value if hasattr(inc, 'severity') else 'info', 0)
            scores.append(score)
        isolated = containment.get('isolated_count', 0)
        risk = (sum(scores) / len(scores)) + (isolated * 5)
        return min(100.0, risk)

    def _determine_status(self, risk: float, containment: Dict[str, Any]) -> OperationalStatus:
        if risk >= 70 and containment.get('isolated_count', 0) > 0:
            return OperationalStatus.CRITICAL
        if risk >= 40:
            return OperationalStatus.DEGRADED
        if containment.get('isolated_count', 0) > 0 or containment.get('quarantined_count', 0) > 0:
            return OperationalStatus.CONTAINED
        return OperationalStatus.HEALTHY

    def reset(self):
        self._containment.clear()
        self._rollback_simulator.clear()
        self._rollback_risk.clear()
        self._dependency_map.clear()
        self._rollback_validator.clear()
        self._escalation.clear()
        self._integrity_guard.clear()
        self._corruption_detector.clear()
        self._partial_state.clear()
        self._consistency.clear()
        self._recommender.clear()
        self._blast_radius.clear()
        self._dependency_impact.clear()
        self._financial_risk.clear()
        self._inventory_risk.clear()
        self._degradation.clear()
        self._router.clear()
        self._execution_engine.clear()
        self._partial_rollback.clear()
        self._external_rollback.clear()
        self._user_override.clear()
        self._incidents.clear()
        self._incident_count = 0
        self._current_tick = 0
