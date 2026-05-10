"""
Decision Intelligence Engine (Phase 13)
Deterministic rule-based system that converts correlated events into
system-level decisions, risk signals, and recommended actions.

NO AI/ML - Pure rule-based deterministic logic.
Consumes output from EventStore, CorrelationEngine, and alert systems.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from django.utils import timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger('erp.decision_engine')

DECISION_CACHE_TTL = 60


@dataclass
class Decision:
    """Structured decision output from the rule engine."""
    decision_id: str
    category: str          # security | performance | ui | system | financial | inventory | sla
    risk_level: str        # critical | high | medium | low
    decision: str          # Human-readable decision statement
    confidence: float      # 0.0 - 1.0 (deterministic score)
    description: str
    recommended_actions: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None
    triggered_by: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            'decision_id': self.decision_id,
            'category': self.category,
            'risk_level': self.risk_level,
            'decision': self.decision,
            'confidence': self.confidence,
            'description': self.description,
            'recommended_actions': self.recommended_actions,
            'correlation_id': self.correlation_id,
            'triggered_by': self.triggered_by,
            'created_at': self.created_at or timezone.now().isoformat(),
        }


class DecisionRuleRegistry:
    """
    Central registry for all decision rules.
    Mirrors RuleRegistry but for decision-level logic.
    """
    _instance = None
    _rules: Dict[str, dict] = {}
    _initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if not DecisionRuleRegistry._initialized:
            self._rules = {}
            self._register_all_rules()
            DecisionRuleRegistry._initialized = True

    def _register_all_rules(self):
        # Security rules
        self._register('security_auth_failure_spike', {
            'category': 'security',
            'description': 'Multiple authentication failures detected',
            'severity': 'critical',
        })
        self._register('security_brute_force', {
            'category': 'security',
            'description': 'Brute force attack pattern detected',
            'severity': 'critical',
        })
        self._register('security_anomaly_detected', {
            'category': 'security',
            'description': 'Security anomaly detected in event stream',
            'severity': 'high',
        })
        self._register('security_session_hijack', {
            'category': 'security',
            'description': 'Potential session hijacking detected',
            'severity': 'critical',
        })

        # Performance rules
        self._register('performance_api_degradation', {
            'category': 'performance',
            'description': 'API performance degradation detected',
            'severity': 'high',
        })
        self._register('performance_api_critical', {
            'category': 'performance',
            'description': 'API response time critically high',
            'severity': 'critical',
        })
        self._register('performance_latency_trend', {
            'category': 'performance',
            'description': 'Latency trend is degrading',
            'severity': 'medium',
        })
        self._register('performance_error_rate', {
            'category': 'performance',
            'description': 'Error rate above threshold',
            'severity': 'high',
        })

        # UI/Frontend rules
        self._register('ui_crash_cluster', {
            'category': 'ui',
            'description': 'Cluster of UI crashes detected',
            'severity': 'high',
        })
        self._register('ui_slow_render', {
            'category': 'ui',
            'description': 'Slow UI rendering detected',
            'severity': 'medium',
        })

        # System rules
        self._register('system_disk_critical', {
            'category': 'system',
            'description': 'Disk usage is critically high',
            'severity': 'critical',
        })
        self._register('system_memory_high', {
            'category': 'system',
            'description': 'Memory usage is above safe threshold',
            'severity': 'high',
        })
        self._register('system_health_degraded', {
            'category': 'system',
            'description': 'Overall system health has degraded',
            'severity': 'high',
        })

        # Financial rules
        self._register('financial_journal_imbalance', {
            'category': 'financial',
            'description': 'Unbalanced journal entries detected',
            'severity': 'critical',
        })

        # Inventory rules
        self._register('inventory_stockout_risk', {
            'category': 'inventory',
            'description': 'Product approaching stockout',
            'severity': 'high',
        })
        self._register('inventory_batch_expiry', {
            'category': 'inventory',
            'description': 'Batches expiring soon',
            'severity': 'medium',
        })

        # SLA rules
        self._register('sla_breach', {
            'category': 'sla',
            'description': 'SLA compliance breach detected',
            'severity': 'critical',
        })
        self._register('sla_warning', {
            'category': 'sla',
            'description': 'SLA compliance at risk',
            'severity': 'high',
        })

    def _register(self, rule_id: str, config: dict):
        self._rules[rule_id] = {**config, 'id': rule_id}

    def get_all_rules(self) -> Dict[str, dict]:
        return self._rules.copy()

    def get_rule(self, rule_id: str) -> Optional[dict]:
        return self._rules.get(rule_id)


class DecisionEngine:
    """
    Core decision engine. Evaluates correlated events and intelligence
    data against registered rules to produce actionable decisions.
    """
    RISK_ORDER = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}

    @classmethod
    def evaluate_all(cls, intelligence: dict = None, events_summary: dict = None) -> List[Decision]:
        """
        Evaluate all decision rules against current intelligence.
        Returns list of active decisions sorted by risk level.
        """
        if intelligence is None:
            intelligence = {}
        if events_summary is None:
            events_summary = {}

        from core.operations.operational_intelligence import (
            OperationalIntelligenceEngine,
            CachedIntelligenceAggregator,
        )

        try:
            full_intel = CachedIntelligenceAggregator.get_all_intelligence()
        except Exception:
            full_intel = intelligence

        anomalies = full_intel.get('anomalies', [])
        alerts = full_intel.get('alerts', {}).get('alerts', [])
        sla_compliance = full_intel.get('sla_monitoring', {})
        trends = full_intel.get('trends', {})
        capacity = full_intel.get('capacity_forecast', {})
        early_warnings = full_intel.get('early_warnings', {}).get('warnings', [])

        decisions: List[Decision] = []
        ts = timezone.now().isoformat()

        # --- Security decisions ---
        auth_anomalies = [a for a in anomalies if 'auth' in a.get('rule', '')]
        if auth_anomalies:
            count = len(auth_anomalies)
            decisions.append(_build_decision(
                'SEC-AUTH-001', 'security', 'critical',
                'Authentication anomaly detected',
                min(count * 0.2, 0.95),
                f'{count} authentication anomaly(ies) detected. Possible brute-force or credential stuffing.',
                ['Review failed auth logs immediately', 'Enable account lockout if not active', 'Consider MFA enforcement'],
                triggered_by=['auth_event', 'anomaly'],
                ts=ts
            ))

        security_anomalies = [a for a in anomalies if a.get('rule', '').startswith('anomaly_failed_auth')]
        if security_anomalies:
            decisions.append(_build_decision(
                'SEC-ANOMALY-001', 'security', 'high',
                'Security anomaly in event stream',
                0.8,
                'Anomalous event patterns detected that may indicate a security incident.',
                ['Isolate affected systems', 'Review access logs', 'Escalate to security team'],
                triggered_by=['anomaly'],
                ts=ts
            ))

        # Check for auth_event errors in recent events
        recent_events = events_summary.get('recent_events', [])
        auth_errors = [e for e in recent_events if e.get('type') == 'auth_event']
        if len(auth_errors) > 5:
            decisions.append(_build_decision(
                'SEC-SESS-001', 'security', 'high',
                'High authentication event volume',
                min(len(auth_errors) * 0.08, 0.85),
                f'{len(auth_errors)} auth events in recent window. Possible session abuse.',
                ['Validate session tokens', 'Review active sessions', 'Rotate compromised tokens if needed'],
                triggered_by=['auth_event'],
                ts=ts
            ))

        # --- Performance decisions ---
        perf_alerts = [a for a in alerts if a.get('type') == 'PERFORMANCE_DEGRADATION']
        if perf_alerts:
            alert = perf_alerts[0]
            mc = alert.get('metric_comparison', {})
            current = mc.get('current_value', 0)
            decisions.append(_build_decision(
                'PERF-DEG-001', 'performance', 'high',
                'API response time degradation detected',
                0.85,
                f'API latency at {current}ms. Performance baseline exceeded.',
                ['Identify slow endpoints via profiling', 'Check database query performance', 'Consider caching layer'],
                triggered_by=['api_request', 'alert'],
                ts=ts
            ))

        latency_trend = trends.get('latency', {})
        if latency_trend.get('trend') == 'degrading':
            decisions.append(_build_decision(
                'PERF-TREND-001', 'performance', 'medium',
                'Latency trend is degrading',
                0.7,
                f'Latency trend shows {latency_trend.get("change_percent", 0):.1f}% degradation.',
                ['Investigate recent deployments', 'Check for resource contention', 'Review load patterns'],
                triggered_by=['trend'],
                ts=ts
            ))

        # SLA violation decisions
        sla_violations = sla_compliance.get('violations', [])
        if sla_violations:
            worst = max(sla_violations, key=lambda v: DecisionEngine.RISK_ORDER.get(v.get('severity', 'low'), 0))
            worst_sev = worst.get('severity', 'high')
            decisions.append(_build_decision(
                'SLA-BREACH-001', 'sla', worst_sev,
                f'SLA violation: {worst.get("type", "unknown")}',
                0.9,
                f'{worst.get("type", "SLA")} SLA violated. Target: {worst.get("target")}, Actual: {worst.get("actual")}.',
                ['Review SLA thresholds', 'Scale affected service', 'Escalate to on-call if critical'],
                triggered_by=['sla'],
                ts=ts
            ))

        # Error rate decisions
        sys_anomalies = [a for a in anomalies if a.get('rule', '') == 'error_rate_spike']
        if sys_anomalies:
            decisions.append(_build_decision(
                'PERF-ERR-001', 'performance', 'high',
                'Error rate spike detected',
                0.85,
                'Application error rate exceeds threshold. Immediate investigation required.',
                ['Check application logs', 'Review recent code changes', 'Rollback if regression'],
                triggered_by=['anomaly', 'error_event'],
                ts=ts
            ))

        # Capacity decisions
        api_forecast = capacity.get('api_traffic', {}).get('linear_forecast', {})
        if api_forecast and api_forecast.get('growth_rate_percent', 0) > 50:
            decisions.append(_build_decision(
                'CAPACITY-API-001', 'system', 'medium',
                'API traffic growth exceeding capacity',
                0.75,
                f'API traffic forecast shows {api_forecast.get("growth_rate_percent", 0):.1f}% growth trend.',
                ['Prepare horizontal scaling plan', 'Review load balancer configuration', 'Set traffic alerts'],
                triggered_by=['capacity'],
                ts=ts
            ))

        # --- System decisions ---
        sys_alerts = [a for a in alerts if a.get('type') == 'CAPACITY_WARNING']
        if sys_alerts:
            memory_alert = next((a for a in sys_alerts if 'Memory' in a.get('title', '')), None)
            disk_alert = next((a for a in sys_alerts if 'Disk' in a.get('title', '')), None)
            if memory_alert:
                decisions.append(_build_decision(
                    'SYS-MEM-001', 'system', 'high',
                    'Memory usage critical',
                    0.85,
                    memory_alert.get('description', 'High memory usage detected.'),
                    ['Identify memory-leaking processes', 'Restart affected services', 'Scale vertically if persistent'],
                    triggered_by=['alert', 'system_event'],
                    ts=ts
                ))
            if disk_alert:
                decisions.append(_build_decision(
                    'SYS-DISK-001', 'system', 'critical',
                    'Disk space critically low',
                    0.95,
                    disk_alert.get('description', 'Critical disk usage detected.'),
                    ['Free disk space immediately', 'Archive old data', 'Expand storage volume'],
                    triggered_by=['alert', 'system_event'],
                    ts=ts
                ))

        # System health degradation
        health_data = full_intel.get('sla_monitoring', {}).get('metrics', {})
        compliance = full_intel.get('sla_monitoring', {}).get('compliance_score', 100)
        if compliance < 70:
            decisions.append(_build_decision(
                'SYS-HEALTH-001', 'system', 'high',
                'Overall system health degraded',
                0.8,
                f'System compliance score at {compliance}%. Multiple SLA thresholds at risk.',
                ['Run full system diagnostics', 'Review all critical alerts', 'Activate incident response'],
                triggered_by=['system_event', 'sla'],
                ts=ts
            ))

        # --- UI decisions ---
        # Check for UI crash clusters in event stream
        ui_errors = [e for e in recent_events if e.get('type') == 'error_event'
                     and 'ui' in str(e.get('module', '')).lower()]
        if len(ui_errors) >= 3:
            decisions.append(_build_decision(
                'UI-CRASH-001', 'ui', 'high',
                'UI error cluster detected',
                0.8,
                f'{len(ui_errors)} UI-related errors in recent event stream.',
                ['Check browser console errors', 'Review recent frontend deployments', 'Test affected user workflows'],
                triggered_by=['error_event'],
                ts=ts
            ))

        # --- Financial decisions ---
        fin_alerts = [a for a in alerts if a.get('type') == 'FINANCIAL_IRREGULARITY']
        if fin_alerts:
            for alert in fin_alerts:
                decisions.append(_build_decision(
                    'FIN-JOURNAL-001', 'financial', 'critical',
                    'Financial data integrity issue',
                    0.9,
                    alert.get('description', 'Financial irregularity detected.'),
                    ['Review affected journal entries', 'Run reconciliation', 'Freeze affected accounts if needed'],
                    triggered_by=['alert'],
                    ts=ts
                ))

        # --- Inventory decisions ---
        inv_alerts = [a for a in alerts if a.get('type') == 'INVENTORY_INCONSISTENCY']
        if inv_alerts:
            for alert in inv_alerts:
                decisions.append(_build_decision(
                    'INV-STOCK-001', 'inventory', alert.get('severity', 'medium'),
                    'Inventory inconsistency detected',
                    0.75,
                    alert.get('description', 'Inventory issue detected.'),
                    ['Verify physical stock counts', 'Check stock sync processes', 'Review batch expiry reports'],
                    triggered_by=['alert'],
                    ts=ts
                ))

        # --- Early warning decisions ---
        for warning in early_warnings:
            signal = warning.get('signal', '')
            sev = warning.get('severity', 'medium')
            decisions.append(_build_decision(
                f'EW-{signal.upper()}-001', warning.get('category', 'system'), sev,
                f'Early warning: {warning.get("description", "Proactive alert")}',
                0.65,
                warning.get('description', 'An early warning signal has been triggered.'),
                ['Monitor closely', 'Prepare preventive action', 'Review trend data'],
                triggered_by=['early_warning'],
                ts=ts
            ))

        # Sort by risk level descending, then by decision_id
        decisions.sort(key=lambda d: (-cls.RISK_ORDER.get(d.risk_level, 0), d.decision_id))

        return decisions

    @classmethod
    def get_decision_summary(cls, decisions: List[Decision] = None) -> dict:
        """Get aggregated summary of decision state."""
        if decisions is None:
            decisions = cls.evaluate_all()

        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        categories = {}
        for d in decisions:
            counts[d.risk_level] = counts.get(d.risk_level, 0) + 1
            cat = d.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        top_decisions = decisions[:10]

        overall_risk = 'low'
        for level in ['critical', 'high', 'medium', 'low']:
            if counts.get(level, 0) > 0:
                overall_risk = level
                break

        return {
            'total_active_decisions': len(decisions),
            'by_risk_level': counts,
            'by_category': categories,
            'overall_risk_level': overall_risk,
            'top_decisions': [d.to_dict() for d in top_decisions],
            'generated_at': timezone.now().isoformat(),
        }

    @classmethod
    def evaluate_events(cls, event_type: str, event_data: dict, correlation_id: str = None) -> List[Decision]:
        """
        Evaluate a specific event or event batch against decision rules.
        Useful for real-time decision generation on event receipt.
        """
        from core.operations.operational_intelligence import OperationalIntelligenceEngine

        decisions = []
        ts = timezone.now().isoformat()

        # Direct event-to-decision mapping
        if event_type == 'auth_event' and event_data.get('action') == 'login_failed':
            if event_data.get('consecutive_failures', 1) >= 5:
                decisions.append(_build_decision(
                    'SEC-AUTH-LOCK-001', 'security', 'critical',
                    'Account lockout threshold reached',
                    0.95,
                    f"Multiple consecutive login failures ({event_data.get('consecutive_failures', '?')}).",
                    ['Lock account for 15 minutes', 'Notify account owner', 'Review auth logs'],
                    correlation_id=correlation_id,
                    triggered_by=[event_type],
                    ts=ts
                ))
            elif event_data.get('consecutive_failures', 1) >= 3:
                decisions.append(_build_decision(
                    'SEC-AUTH-WARN-001', 'security', 'high',
                    'Suspicious login activity',
                    0.75,
                    f"Login failures detected ({event_data.get('consecutive_failures', '?')} consecutive).",
                    ['Monitor account closely', 'Send user notification', 'Challenge with MFA'],
                    correlation_id=correlation_id,
                    triggered_by=[event_type],
                    ts=ts
                ))

        if event_type == 'api_request' and event_data.get('duration_ms', 0) > 5000:
            decisions.append(_build_decision(
                'PERF-SLOW-001', 'performance', 'high',
                'Extremely slow API request',
                0.8,
                f"API request took {event_data.get('duration_ms', 0)}ms (threshold: 5000ms).",
                ['Profile the endpoint', 'Check database query efficiency', 'Add caching if appropriate'],
                correlation_id=correlation_id,
                triggered_by=[event_type],
                ts=ts
            ))

        if event_type == 'error_event':
            error_module = event_data.get('module', '')
            error_count = event_data.get('count', 1)
            if error_count >= 10:
                decisions.append(_build_decision(
                    'PERF-ERR-CLUSTER-001', 'performance', 'high',
                    f'Error burst in {error_module}',
                    0.85,
                    f"{error_count} errors detected in {error_module}.",
                    ['Check application logs', 'Investigate root cause', 'Rollback recent changes if needed'],
                    correlation_id=correlation_id,
                    triggered_by=[event_type],
                    ts=ts
                ))

        if event_type == 'crash_event':
            decisions.append(_build_decision(
                'SYS-CRASH-001', 'system', 'critical',
                'Application crash detected',
                0.99,
                f"Unhandled crash: {event_data.get('message', 'Unknown')}",
                ['Check crash logs', 'Restart affected service', 'Investigate root cause'],
                correlation_id=correlation_id,
                triggered_by=[event_type],
                ts=ts
            ))

        return decisions


def _build_decision(
    decision_id: str,
    category: str,
    risk_level: str,
    decision: str,
    confidence: float,
    description: str,
    recommended_actions: List[str],
    triggered_by: List[str],
    ts: str,
    correlation_id: Optional[str] = None,
) -> Decision:
    return Decision(
        decision_id=decision_id,
        category=category,
        risk_level=risk_level,
        decision=decision,
        confidence=round(confidence, 2),
        description=description,
        recommended_actions=recommended_actions,
        correlation_id=correlation_id,
        triggered_by=triggered_by,
        created_at=ts,
    )


# Convenience wrappers
def get_active_decisions() -> List[Decision]:
    """Get all currently active decisions."""
    return DecisionEngine.evaluate_all()


def get_decision_summary() -> dict:
    """Get aggregated decision summary."""
    return DecisionEngine.get_decision_summary()


def evaluate_event_decisions(event_type: str, event_data: dict = None, correlation_id: str = None) -> List[Decision]:
    """Evaluate decisions for a specific event."""
    return DecisionEngine.evaluate_events(event_type, event_data or {}, correlation_id)