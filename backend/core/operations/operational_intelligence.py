"""
Advanced Operational Intelligence Layer.
Deterministic rule-based analytics for predictive insights.
NO AI/ML - Pure rule-based deterministic logic.

Phase 12 Components:
1. Anomaly Detection (done)
2. Trend Identification (done)
3. SLA Monitoring Engine
4. Capacity Forecast Engine
5. Intelligence Alert System
6. Cached Intelligence Aggregator
7. Rule Registry System (Phase 12.1)

Phase 12.1 - Rule Governance:
- RuleRegistry: Centralized rule management
- All rules migrated to single source of truth
- Duplicate detection and prevention
- Rule metadata (category, severity, enabled, description)
"""
import logging
import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from typing import Optional, Dict, Any, List


logger = logging.getLogger('erp.operational_intelligence')


INTELLIGENCE_CACHE_TTL = 60
CACHE_PREFIX = 'op_intel_'


class RuleRegistry:
    """
    Centralized Rule Governance System.
    Single source of truth for all operational intelligence rules.
    Prevents rule explosion and duplication.
    """

    _instance = None
    _rules: Dict[str, dict] = {}
    _initialized = False

    CATEGORIES = {
        'PERFORMANCE': 'performance',
        'RESOURCE': 'resource',
        'SECURITY': 'security',
        'FINANCIAL': 'financial',
        'INVENTORY': 'inventory',
        'SLA': 'sla',
        'TREND': 'trend',
        'CAPACITY': 'capacity'
    }

    SEVERITIES = ['critical', 'high', 'medium', 'low']

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if not RuleRegistry._initialized:
            self._rules = {}
            self._register_all_rules()
            RuleRegistry._initialized = True

    def _register_all_rules(self):
        self._register_rule('anomaly_error_rate_spike', {
            'category': 'PERFORMANCE',
            'severity': 'high',
            'description': 'High error rate detected (>10 errors/minute)',
            'condition': 'errors_per_minute > 10',
            'window_minutes': 5,
            'enabled': True,
            'module': 'anomaly_detector'
        })
        self._register_rule('anomaly_latency_spike', {
            'category': 'PERFORMANCE',
            'severity': 'high',
            'description': 'API latency spike (>2000ms)',
            'condition': 'avg_latency_ms > 2000',
            'window_minutes': 5,
            'enabled': True,
            'module': 'anomaly_detector'
        })
        self._register_rule('anomaly_memory_high', {
            'category': 'RESOURCE',
            'severity': 'medium',
            'description': 'Memory usage high (>85%)',
            'condition': 'memory_percent > 85',
            'window_minutes': 1,
            'enabled': True,
            'module': 'anomaly_detector'
        })
        self._register_rule('anomaly_disk_critical', {
            'category': 'RESOURCE',
            'severity': 'critical',
            'description': 'Disk usage critical (>95%)',
            'condition': 'disk_percent > 95',
            'window_minutes': 1,
            'enabled': True,
            'module': 'anomaly_detector'
        })
        self._register_rule('anomaly_failed_auth_spike', {
            'category': 'SECURITY',
            'severity': 'high',
            'description': 'Failed authentication spike (>5/minute)',
            'condition': 'failed_auth_per_minute > 5',
            'window_minutes': 2,
            'enabled': True,
            'module': 'anomaly_detector'
        })
        self._register_rule('anomaly_stock_depletion', {
            'category': 'INVENTORY',
            'severity': 'medium',
            'description': 'Stock level below minimum threshold',
            'condition': 'stock_level < minimum * 1.2',
            'window_minutes': 60,
            'enabled': True,
            'module': 'anomaly_detector'
        })
        self._register_rule('anomaly_batch_expiry', {
            'category': 'INVENTORY',
            'severity': 'medium',
            'description': 'Batches expiring within 7 days',
            'condition': 'batches_expiring_in_days < 7',
            'window_minutes': 60,
            'enabled': True,
            'module': 'anomaly_detector'
        })
        self._register_rule('anomaly_journal_unbalanced', {
            'category': 'FINANCIAL',
            'severity': 'critical',
            'description': 'Unbalanced journal entries detected',
            'condition': 'unbalanced_entries > 0',
            'window_minutes': 1,
            'enabled': True,
            'module': 'anomaly_detector'
        })

        self._register_rule('sla_api_uptime', {
            'category': 'SLA',
            'severity': 'critical',
            'description': 'API uptime below 95% (critical) or 99.9% (target)',
            'target': 99.9,
            'critical': 95.0,
            'enabled': True,
            'module': 'sla_monitor'
        })
        self._register_rule('sla_response_time', {
            'category': 'SLA',
            'severity': 'high',
            'description': 'Response time exceeds target (500ms) or critical (1500ms)',
            'target': 500,
            'critical': 1500,
            'enabled': True,
            'module': 'sla_monitor'
        })
        self._register_rule('sla_error_rate', {
            'category': 'SLA',
            'severity': 'high',
            'description': 'Error rate exceeds target (1%) or critical (5%)',
            'target': 1.0,
            'critical': 5.0,
            'enabled': True,
            'module': 'sla_monitor'
        })

        self._register_rule('warning_latency_degrading', {
            'category': 'TREND',
            'severity': 'warning',
            'description': 'Latency trend degrading (>30% increase)',
            'metric': 'latency_trend',
            'threshold': 'degrading',
            'enabled': True,
            'module': 'early_warning'
        })
        self._register_rule('warning_error_increase', {
            'category': 'TREND',
            'severity': 'high',
            'description': 'Error rate trend increasing (>50%)',
            'metric': 'error_trend',
            'threshold': 'degrading',
            'enabled': True,
            'module': 'early_warning'
        })
        self._register_rule('warning_stock_depleting', {
            'category': 'INVENTORY',
            'severity': 'medium',
            'description': 'Stock level depleting (>20% decline)',
            'metric': 'stock_trend',
            'threshold': 'depleting',
            'enabled': True,
            'module': 'early_warning'
        })
        self._register_rule('warning_unbalanced_journal', {
            'category': 'FINANCIAL',
            'severity': 'critical',
            'description': 'Unbalanced journal entries detected',
            'metric': 'unbalanced_entries',
            'threshold': 0,
            'enabled': True,
            'module': 'early_warning'
        })

        self._register_rule('capacity_memory_threshold', {
            'category': 'CAPACITY',
            'severity': 'high',
            'description': 'Memory usage above threshold',
            'threshold': 85,
            'enabled': True,
            'module': 'alert_system'
        })
        self._register_rule('capacity_disk_threshold', {
            'category': 'CAPACITY',
            'severity': 'critical',
            'description': 'Disk usage critical',
            'threshold': 90,
            'enabled': True,
            'module': 'alert_system'
        })

    def _register_rule(self, rule_id: str, rule_config: dict):
        rule_key = f"{rule_config.get('module', 'unknown')}.{rule_id}"
        if rule_key in self._rules:
            logger.warning(f"Duplicate rule detected: {rule_key}, skipping registration")
            return
        self._rules[rule_key] = {
            'id': rule_id,
            'key': rule_key,
            **rule_config
        }

    def get_rule(self, rule_key: str) -> Optional[dict]:
        return self._rules.get(rule_key)

    def get_all_rules(self) -> Dict[str, dict]:
        return self._rules.copy()

    def get_rules_by_category(self, category: str) -> Dict[str, dict]:
        return {
            k: v for k, v in self._rules.items()
            if v.get('category') == category.upper()
        }

    def get_rules_by_module(self, module: str) -> Dict[str, dict]:
        return {
            k: v for k, v in self._rules.items()
            if v.get('module') == module
        }

    def get_enabled_rules(self) -> Dict[str, dict]:
        return {
            k: v for k, v in self._rules.items()
            if v.get('enabled', True)
        }

    def get_rule_count(self) -> int:
        return len(self._rules)

    def get_categories(self) -> List[str]:
        return list(set(r.get('category') for r in self._rules.values()))

    def get_modules(self) -> List[str]:
        return list(set(r.get('module') for r in self._rules.values()))

    def enable_rule(self, rule_key: str) -> bool:
        if rule_key in self._rules:
            self._rules[rule_key]['enabled'] = True
            return True
        return False

    def disable_rule(self, rule_key: str) -> bool:
        if rule_key in self._rules:
            self._rules[rule_key]['enabled'] = False
            return True
        return False

    def validate_rule(self, rule_key: str) -> dict:
        if rule_key not in self._rules:
            return {'valid': False, 'error': 'Rule not found'}

        rule = self._rules[rule_key]
        errors = []

        if not rule.get('category'):
            errors.append('Missing category')
        if not rule.get('severity'):
            errors.append('Missing severity')
        elif rule['severity'] not in self.SEVERITIES:
            errors.append(f'Invalid severity: {rule["severity"]}')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'rule': rule
        }

    def get_registry_summary(self) -> dict:
        return {
            'total_rules': len(self._rules),
            'enabled_count': sum(1 for r in self._rules.values() if r.get('enabled', True)),
            'categories': self.get_categories(),
            'modules': self.get_modules(),
            'by_category': {
                cat: len([r for r in self._rules.values() if r.get('category') == cat])
                for cat in self.get_categories()
            },
            'by_module': {
                mod: len([r for r in self._rules.values() if r.get('module') == mod])
                for mod in self.get_modules()
            }
        }


class RuleBasedAnomalyDetector:
    """
    Deterministic anomaly detection using statistical rules.
    NOT AI - pure threshold-based detection.
    Uses RuleRegistry for centralized rule management.
    """

    @classmethod
    def get_rules_from_registry(cls) -> dict:
        registry = RuleRegistry.get_instance()
        return registry.get_rules_by_module('anomaly_detector')

    @classmethod
    def evaluate_rules(cls, metrics: dict) -> list:
        """Evaluate all rules from registry against metrics."""
        detected = []

        for rule_key, rule_config in cls.get_rules_from_registry().items():
            if not rule_config.get('enabled', True):
                continue
            result = cls._evaluate_single_rule(rule_config.get('id', rule_key), rule_config, metrics)
            if result:
                detected.append(result)

        return detected

    @classmethod
    def _evaluate_single_rule(cls, rule_name: str, rule_config: dict, metrics: dict) -> dict:
        """Evaluate a single rule."""
        severity = rule_config.get('severity', 'low')
        rule_id = rule_config.get('id', rule_name)

        base_name = rule_id.replace('anomaly_', '')

        if base_name == 'error_rate_spike':
            errors = metrics.get('errors_per_minute', 0)
            if errors > 10:
                return {
                    'rule': 'error_rate_spike',
                    'severity': severity,
                    'condition_met': f"errors_per_minute={errors} > 10",
                    'recommendation': 'Check API logs immediately'
                }

        elif base_name == 'latency_spike':
            latency = metrics.get('avg_latency_ms', 0)
            if latency > 2000:
                return {
                    'rule': 'latency_spike',
                    'severity': severity,
                    'condition_met': f"latency={latency}ms > 2000ms",
                    'recommendation': 'Review slow endpoints'
                }

        elif base_name == 'memory_high':
            memory = metrics.get('memory_percent', 0)
            if memory > 85:
                return {
                    'rule': 'memory_usage_high',
                    'severity': severity,
                    'condition_met': f"memory={memory}% > 85%",
                    'recommendation': 'Scale resources or optimize'
                }

        elif base_name == 'disk_critical':
            disk = metrics.get('disk_percent', 0)
            if disk > 95:
                return {
                    'rule': 'disk_usage_critical',
                    'severity': severity,
                    'condition_met': f"disk={disk}% > 95%",
                    'recommendation': 'URGENT: Free disk space'
                }

        elif base_name == 'failed_auth_spike':
            failed_auth = metrics.get('failed_auth_per_minute', 0)
            if failed_auth > 5:
                return {
                    'rule': 'failed_authentication_spike',
                    'severity': severity,
                    'condition_met': f"failed_auth={failed_auth} > 5",
                    'recommendation': 'Possible brute force attack'
                }

        elif base_name == 'journal_unbalanced':
            unbalanced = metrics.get('unbalanced_entries', 0)
            if unbalanced > 0:
                return {
                    'rule': 'journal_unbalanced',
                    'severity': severity,
                    'condition_met': f"unbalanced={unbalanced} > 0",
                    'recommendation': 'Review journal entries'
                }

        return None


class TrendIdentifier:
    """
    Identify trends using statistical rules.
    Simple linear trend detection without AI.
    """

    @staticmethod
    def detect_latency_trend(latency_history: list) -> dict:
        """Detect latency trend using simple slope analysis."""
        if len(latency_history) < 3:
            return {'trend': 'insufficient_data'}

        values = [l.get('avg_ms', 0) for l in latency_history[-10:]]
        if not values:
            return {'trend': 'insufficient_data'}

        first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
        second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

        change_percent = ((second_half_avg - first_half_avg) / max(first_half_avg, 1)) * 100

        trend = 'stable'
        if change_percent > 30:
            trend = 'degrading'
        elif change_percent < -20:
            trend = 'improving'

        return {
            'trend': trend,
            'change_percent': round(change_percent, 2),
            'first_half_avg': round(first_half_avg, 2),
            'second_half_avg': round(second_half_avg, 2)
        }

    @staticmethod
    def detect_error_trend(error_history: list) -> dict:
        """Detect error rate trend."""
        if len(error_history) < 3:
            return {'trend': 'insufficient_data'}

        values = [e.get('count', 0) for e in error_history[-10:]]
        if not values:
            return {'trend': 'insufficient_data'}

        total_errors = sum(values)
        avg_errors = total_errors / len(values)

        trend = 'stable'
        if avg_errors > 20:
            trend = 'critical'
        elif avg_errors > 10:
            trend = 'degrading'

        return {
            'trend': trend,
            'total_errors': total_errors,
            'avg_per_period': round(avg_errors, 2)
        }

    @staticmethod
    def detect_stock_trend(stock_levels: list) -> dict:
        """Detect inventory level trend."""
        if len(stock_levels) < 3:
            return {'trend': 'insufficient_data'}

        values = [s.get('total_quantity', 0) for s in stock_levels[-10:]]
        if not values:
            return {'trend': 'insufficient_data'}

        latest = values[-1]
        oldest = values[0]

        if latest == 0:
            return {'trend': 'depleted'}

        change_percent = ((latest - oldest) / oldest) * 100

        trend = 'stable'
        if change_percent < -30:
            trend = 'depleting_fast'
        elif change_percent < -10:
            trend = 'depleting'

        return {
            'trend': trend,
            'change_percent': round(change_percent, 2),
            'current_level': latest
        }


class RiskPredictor:
    """
    Predict risks using deterministic rules.
    NOT AI - pure threshold-based prediction.
    """

    @staticmethod
    def predict_sla_violation(current_latency: float, sla_threshold: float, trend: str) -> dict:
        """Predict SLA violation probability."""
        base_score = 0

        if current_latency > sla_threshold * 0.8:
            base_score += 30
        if current_latency > sla_threshold:
            base_score += 50
        if trend == 'degrading':
            base_score += 20

        probability = min(100, base_score)

        return {
            'sla_threshold_ms': sla_threshold,
            'current_latency_ms': current_latency,
            'trend': trend,
            'violation_probability_percent': probability,
            'risk_level': 'high' if probability > 70 else 'medium' if probability > 40 else 'low'
        }

    @staticmethod
    def predict_stockout(product_id: str, stock_level: float, daily_usage: float, lead_time_days: int) -> dict:
        """Predict stockout risk."""
        if daily_usage == 0:
            days_remaining = 999
            risk = 'none'
        else:
            days_remaining = stock_level / daily_usage
            if days_remaining < lead_time_days:
                risk = 'critical'
            elif days_remaining < lead_time_days * 1.5:
                risk = 'high'
            elif days_remaining < lead_time_days * 2:
                risk = 'medium'
            else:
                risk = 'low'

        return {
            'product_id': product_id,
            'current_stock': stock_level,
            'daily_usage': daily_usage,
            'lead_time_days': lead_time_days,
            'days_until_stockout': round(days_remaining, 1),
            'risk_level': risk,
            'action_required': risk in ['critical', 'high']
        }

    @staticmethod
    def predict_journal_imbalance_risk(unbalanced_count: int, total_entries: int) -> dict:
        """Predict financial data integrity risk."""
        if total_entries == 0:
            risk = 'none'
            probability = 0
        else:
            ratio = unbalanced_count / total_entries
            if ratio > 0.05:
                risk = 'critical'
                probability = 95
            elif ratio > 0.02:
                risk = 'high'
                probability = 70
            elif ratio > 0:
                risk = 'medium'
                probability = 40
            else:
                risk = 'none'
                probability = 0

        return {
            'unbalanced_entries': unbalanced_count,
            'total_entries': total_entries,
            'risk_level': risk,
            'integrity_probability_percent': 100 - probability
        }

    @staticmethod
    def predict_batch_expiry_risk(expired_count: int, expiring_soon_count: int, total_batches: int) -> dict:
        """Predict batch expiry risk."""
        at_risk = expired_count + expiring_soon_count

        if total_batches == 0:
            risk = 'none'
        elif at_risk / total_batches > 0.3:
            risk = 'critical'
        elif at_risk / total_batches > 0.1:
            risk = 'high'
        elif at_risk > 0:
            risk = 'medium'
        else:
            risk = 'none'

        return {
            'expired_count': expired_count,
            'expiring_soon_count': expiring_soon_count,
            'total_batches': total_batches,
            'at_risk_percent': round((at_risk / max(total_batches, 1)) * 100, 2),
            'risk_level': risk
        }


class SLAComplianceMonitor:
    """Monitor SLA compliance using deterministic rules."""

    SLAS = {
        'api_response_time': {'warning': 500, 'critical': 1500},
        'database_query_time': {'warning': 200, 'critical': 1000},
        'report_generation_time': {'warning': 5000, 'critical': 15000},
        'payment_processing_time': {'warning': 1000, 'critical': 5000},
    }

    @classmethod
    def check_sla_compliance(cls, metric_type: str, value: float) -> dict:
        """Check if metric meets SLA."""
        if metric_type not in cls.SLAS:
            return {'status': 'unknown', 'metric': metric_type}

        thresholds = cls.SLAS[metric_type]

        if value > thresholds['critical']:
            status = 'violated'
            compliance_percent = 0
        elif value > thresholds['warning']:
            status = 'warning'
            compliance_percent = 50
        else:
            status = 'compliant'
            compliance_percent = 100

        return {
            'metric': metric_type,
            'value': value,
            'threshold_warning': thresholds['warning'],
            'threshold_critical': thresholds['critical'],
            'status': status,
            'compliance_percent': compliance_percent
        }

    @classmethod
    def get_overall_sla_health(cls, metrics: dict) -> dict:
        """Calculate overall SLA health."""
        results = []

        for metric_type, value in metrics.items():
            result = cls.check_sla_compliance(metric_type, value)
            results.append(result)

        compliant_count = sum(1 for r in results if r.get('status') == 'compliant')
        total_count = len(results)

        overall_compliance = (compliant_count / max(total_count, 1)) * 100

        return {
            'overall_compliance_percent': round(overall_compliance, 2),
            'metrics_checked': total_count,
            'compliant': compliant_count,
            'violated': total_count - compliant_count,
            'details': results
        }


class EarlyWarningSystem:
    """
    Early warning signals based on deterministic rules.
    Provides proactive alerts before issues become critical.
    Uses RuleRegistry for centralized rule management.
    """

    @classmethod
    def get_warning_rules(cls) -> dict:
        registry = RuleRegistry.get_instance()
        return registry.get_rules_by_module('early_warning')

    @classmethod
    def get_early_warnings(cls, metrics: dict) -> dict:
        """Get all active early warnings based on registry rules."""
        warnings = []
        warning_rules = cls.get_warning_rules()

        signal_name_map = {
            'warning_latency_degrading': 'slow_api_trend',
            'warning_error_increase': 'error_rate_increase',
            'warning_stock_depleting': 'depletion_trend',
            'warning_unbalanced_journal': 'unbalanced_journal'
        }

        for rule_key, rule in warning_rules.items():
            if not rule.get('enabled', True):
                continue

            metric_key = rule.get('metric')
            threshold = rule.get('threshold')
            rule_id = rule.get('id', '')
            signal_name = signal_name_map.get(rule_id, rule_id)

            if metric_key == 'latency_trend' and metrics.get('latency_trend') == threshold:
                warnings.append({
                    'category': rule.get('category', 'performance'),
                    'signal': signal_name,
                    'description': rule.get('description', 'Latency trend issue'),
                    'severity': rule.get('severity', 'warning')
                })

            elif metric_key == 'error_trend' and metrics.get('error_trend') == threshold:
                warnings.append({
                    'category': rule.get('category', 'performance'),
                    'signal': signal_name,
                    'description': rule.get('description', 'Error trend issue'),
                    'severity': rule.get('severity', 'high')
                })

            elif metric_key == 'stock_trend' and metrics.get('stock_trend') == threshold:
                warnings.append({
                    'category': rule.get('category', 'inventory'),
                    'signal': signal_name,
                    'description': rule.get('description', 'Stock trend issue'),
                    'severity': rule.get('severity', 'medium')
                })

            elif metric_key == 'unbalanced_entries' and metrics.get('unbalanced_entries', 0) > threshold:
                warnings.append({
                    'category': rule.get('category', 'financial'),
                    'signal': signal_name,
                    'description': rule.get('description', 'Journal imbalance'),
                    'severity': rule.get('severity', 'critical')
                })

        return {
            'active_warnings': len(warnings),
            'warnings': warnings,
            'signal_categories': list(set(w.get('category') for w in warnings))
        }


class OperationalIntelligenceEngine:
    """Combine all deterministic intelligence."""

    @classmethod
    def get_complete_intelligence(cls, metrics: dict) -> dict:
        """Get comprehensive operational intelligence."""
        return {
            'anomalies': RuleBasedAnomalyDetector.evaluate_rules(metrics),
            'trends': {
                'latency': TrendIdentifier.detect_latency_trend(metrics.get('latency_history', [])),
                'errors': TrendIdentifier.detect_error_trend(metrics.get('error_history', [])),
                'stock': TrendIdentifier.detect_stock_trend(metrics.get('stock_history', []))
            },
            'sla_compliance': SLAComplianceMonitor.get_overall_sla_health(metrics.get('sla_metrics', {})),
            'early_warnings': EarlyWarningSystem.get_early_warnings(metrics),
            'generated_at': timezone.now().isoformat()
        }


def get_operational_intelligence(metrics: dict = None) -> dict:
    """Public interface to operational intelligence."""
    if metrics is None:
        metrics = {}

    return OperationalIntelligenceEngine.get_complete_intelligence(metrics)


class SLAMonitoringEngine:
    """
    Track system SLA compliance.
    SLA RULES:
    - API uptime target: 99.9%
    - Response time target: <500ms normal
    - Error rate target: <1%
    Uses RuleRegistry for centralized rule management.
    """

    @classmethod
    def get_sla_targets(cls) -> dict:
        registry = RuleRegistry.get_instance()
        rules = registry.get_rules_by_module('sla_monitor')
        targets = {}
        for rule_key, rule in rules.items():
            rule_id = rule.get('id', '').replace('sla_', '')
            targets[rule_id] = {
                'target': rule.get('target', 0),
                'critical': rule.get('critical', 0)
            }
        if not targets:
            targets = {
                'api_uptime_percent': {'target': 99.9, 'critical': 95.0},
                'response_time_ms': {'target': 500, 'critical': 1500},
                'error_rate_percent': {'target': 1.0, 'critical': 5.0},
            }
        return targets

    @classmethod
    def calculate_compliance_score(cls, metrics: dict) -> dict:
        """Calculate overall SLA compliance score (0-100)."""
        scores = []
        violations = []

        sla_targets = cls.get_sla_targets()

        uptime = metrics.get('api_uptime_percent', 100)
        uptime_target = sla_targets.get('api_uptime_percent', {}).get('target', 99.9)
        uptime_critical = sla_targets.get('api_uptime_percent', {}).get('critical', 95.0)

        if uptime < uptime_critical:
            scores.append(0)
            violations.append({
                'type': 'api_uptime',
                'target': uptime_target,
                'actual': uptime,
                'severity': 'critical'
            })
        elif uptime < uptime_target:
            scores.append(50)
            violations.append({
                'type': 'api_uptime',
                'target': uptime_target,
                'actual': uptime,
                'severity': 'warning'
            })
        else:
            scores.append(100)

        response_time = metrics.get('response_time_ms', 0)
        response_target = sla_targets.get('response_time_ms', {}).get('target', 500)
        response_critical = sla_targets.get('response_time_ms', {}).get('critical', 1500)

        if response_time > response_critical:
            scores.append(0)
            violations.append({
                'type': 'response_time',
                'target': response_target,
                'actual': response_time,
                'severity': 'critical'
            })
        elif response_time > response_target:
            scores.append(50)
            violations.append({
                'type': 'response_time',
                'target': response_target,
                'actual': response_time,
                'severity': 'warning'
            })
        else:
            scores.append(100)

        error_rate = metrics.get('error_rate_percent', 0)
        error_target = sla_targets.get('error_rate_percent', {}).get('target', 1.0)
        error_critical = sla_targets.get('error_rate_percent', {}).get('critical', 5.0)

        if error_rate > error_critical:
            scores.append(0)
            violations.append({
                'type': 'error_rate',
                'target': error_target,
                'actual': error_rate,
                'severity': 'critical'
            })
        elif error_rate > error_target:
            scores.append(50)
            violations.append({
                'type': 'error_rate',
                'target': error_target,
                'actual': error_rate,
                'severity': 'warning'
            })
        else:
            scores.append(100)

        overall_score = sum(scores) / len(scores) if scores else 100

        return {
            'compliance_score': round(overall_score, 2),
            'violations': violations,
            'violation_count': len(violations),
            'targets': sla_targets,
            'metrics': {
                'api_uptime_percent': uptime,
                'response_time_ms': response_time,
                'error_rate_percent': error_rate
            }
        }

    @classmethod
    def get_degradation_timeline(cls, history: list) -> dict:
        """Build degradation timeline from historical data."""
        if len(history) < 2:
            return {'timeline': [], 'degradation_detected': False}

        timeline = []
        for i, h in enumerate(history):
            score = 100
            if h.get('response_time_ms', 0) > 500:
                score -= 20
            if h.get('error_rate_percent', 0) > 1:
                score -= 30
            if h.get('api_uptime_percent', 100) < 99.9:
                score -= min(30, 100 - h.get('api_uptime_percent', 100))

            timeline.append({
                'timestamp': h.get('timestamp', f'point_{i}'),
                'score': max(0, score),
                'status': 'degraded' if score < 70 else 'stable'
            })

        degraded_points = sum(1 for t in timeline if t['status'] == 'degraded')

        return {
            'timeline': timeline,
            'degradation_detected': degraded_points > len(timeline) * 0.3,
            'degraded_periods': degraded_points
        }


class CapacityForecastEngine:
    """
    Statistical capacity forecasting.
    NO AI - pure linear extrapolation and moving average.
    """

    @staticmethod
    def linear_extrapolation(values: list, periods_ahead: int = 4) -> dict:
        """Linear growth projection using least squares."""
        if len(values) < 3:
            return {'forecast': [], 'growth_rate_percent': 0, 'confidence': 'low'}

        n = len(values)
        indices = list(range(n))

        sum_x = sum(indices)
        sum_y = sum(values)
        sum_xy = sum(i * v for i, v in zip(indices, values))
        sum_xx = sum(i * i for i in indices)

        slope = (n * sum_xy - sum_x * sum_y) / max(n * sum_xx - sum_x * sum_x, 1)
        intercept = (sum_y - slope * sum_x) / n

        forecast = []
        for i in range(1, periods_ahead + 1):
            predicted = intercept + slope * (n - 1 + i)
            forecast.append(max(0, round(predicted, 2)))

        avg_value = sum(values) / n
        growth_rate = (slope / max(avg_value, 1)) * 100 if avg_value > 0 else 0

        confidence = 'high' if n >= 10 else 'medium' if n >= 5 else 'low'

        return {
            'forecast': forecast,
            'growth_rate_percent': round(growth_rate, 2),
            'slope': round(slope, 4),
            'confidence': confidence,
            'base_value': round(intercept, 2)
        }

    @staticmethod
    def moving_average_trend(values: list, window: int = 3) -> dict:
        """Detect trend using moving average comparison."""
        if len(values) < window * 2:
            return {'trend': 'insufficient_data', 'direction': 'unknown'}

        recent_ma = sum(values[-window:]) / window
        older_ma = sum(values[-window*2:-window]) / window

        change_percent = ((recent_ma - older_ma) / max(older_ma, 1)) * 100

        direction = 'stable'
        if change_percent > 10:
            direction = 'increasing'
        elif change_percent < -10:
            direction = 'decreasing'

        return {
            'trend': direction,
            'change_percent': round(change_percent, 2),
            'recent_ma': round(recent_ma, 2),
            'older_ma': round(older_ma, 2),
            'window': window
        }

    @staticmethod
    def historical_comparison(current: float, historical_avg: float) -> dict:
        """Compare current value to historical average."""
        if historical_avg == 0:
            return {'comparison': 'unknown', 'delta_percent': 0}

        delta_percent = ((current - historical_avg) / historical_avg) * 100

        comparison = 'normal'
        if delta_percent > 50:
            comparison = 'significant_spike'
        elif delta_percent > 20:
            comparison = 'elevated'
        elif delta_percent < -50:
            comparison = 'significant_drop'
        elif delta_percent < -20:
            comparison = 'depressed'

        return {
            'comparison': comparison,
            'delta_percent': round(delta_percent, 2),
            'current': current,
            'historical_avg': historical_avg
        }

    @classmethod
    def forecast_capacity(cls, metrics: dict) -> dict:
        """Comprehensive capacity forecast."""
        api_requests = metrics.get('api_requests_history', [])
        db_size_history = metrics.get('db_size_history', [])
        storage_history = metrics.get('storage_history', [])

        api_forecast = cls.linear_extrapolation(api_requests) if api_requests else {}
        db_forecast = cls.linear_extrapolation(db_size_history) if db_size_history else {}

        api_ma = cls.moving_average_trend(api_requests) if api_requests else {}
        storage_ma = cls.moving_average_trend(storage_history) if storage_history else {}

        return {
            'api_traffic': {
                'linear_forecast': api_forecast,
                'trend_ma': api_ma
            },
            'database': {
                'linear_forecast': db_forecast,
                'size_forecast_gb': db_forecast.get('forecast', [None])[0] if db_forecast else None
            },
            'storage': {
                'trend_ma': storage_ma
            },
            'generated_at': timezone.now().isoformat()
        }


class IntelligenceAlertSystem:
    """
    Generate structured alerts.
    ALERT TYPES:
    - PERFORMANCE_DEGRADATION
    - SYSTEM_ANOMALY
    - CAPACITY_WARNING
    - FINANCIAL_IRREGULARITY
    - INVENTORY_INCONSISTENCY
    """

    ALERT_TYPES = [
        'PERFORMANCE_DEGRADATION',
        'SYSTEM_ANOMALY',
        'CAPACITY_WARNING',
        'FINANCIAL_IRREGULARITY',
        'INVENTORY_INCONSISTENCY'
    ]

    @classmethod
    def create_alert(cls, alert_type: str, title: str, description: str,
                     metric_value: float, baseline_value: float,
                     severity: str = 'medium') -> dict:
        """Create structured alert with full context."""
        return {
            'type': alert_type,
            'title': title,
            'description': description,
            'metric_comparison': {
                'current_value': metric_value,
                'baseline_value': baseline_value,
                'delta_percent': round(((metric_value - baseline_value) / max(baseline_value, 1)) * 100, 2)
            },
            'baseline_reference': baseline_value,
            'timestamp': timezone.now().isoformat(),
            'severity': severity,
            'requires_action': severity in ['high', 'critical']
        }

    @classmethod
    def analyze_and_generate_alerts(cls, metrics: dict, baselines: dict = None) -> dict:
        """Analyze metrics and generate appropriate alerts."""
        if baselines is None:
            baselines = {}

        response_time_baseline = baselines.get('response_time_ms', 200)
        error_rate_baseline = baselines.get('error_rate_percent', 0.5)
        memory_baseline = baselines.get('memory_percent', 60)
        disk_baseline = baselines.get('disk_percent', 50)

        alerts = []

        response_time = metrics.get('response_time_ms', 0)
        if response_time > response_time_baseline * 2:
            alerts.append(cls.create_alert(
                'PERFORMANCE_DEGRADATION',
                'Response Time Degradation',
                f'API response time is {response_time}ms, exceeding baseline',
                response_time,
                response_time_baseline,
                'high'
            ))

        error_rate = metrics.get('error_rate_percent', 0)
        if error_rate > error_rate_baseline * 3:
            alerts.append(cls.create_alert(
                'SYSTEM_ANOMALY',
                'Error Rate Anomaly',
                f'Error rate {error_rate}% is 3x above baseline',
                error_rate,
                error_rate_baseline,
                'critical'
            ))

        memory = metrics.get('memory_percent', 0)
        if memory > 85:
            alerts.append(cls.create_alert(
                'CAPACITY_WARNING',
                'Memory Usage High',
                f'Memory at {memory}%, approaching capacity',
                memory,
                memory_baseline,
                'high'
            ))

        disk = metrics.get('disk_percent', 0)
        if disk > 90:
            alerts.append(cls.create_alert(
                'CAPACITY_WARNING',
                'Disk Space Critical',
                f'Disk usage at {disk}%, critical capacity warning',
                disk,
                disk_baseline,
                'critical'
            ))

        unbalanced = metrics.get('unbalanced_entries', 0)
        if unbalanced > 0:
            alerts.append(cls.create_alert(
                'FINANCIAL_IRREGULARITY',
                'Unbalanced Journal Entries',
                f'{unbalanced} unbalanced journal entries detected',
                unbalanced,
                0,
                'critical'
            ))

        low_stock_count = metrics.get('low_stock_products', 0)
        if low_stock_count > 5:
            alerts.append(cls.create_alert(
                'INVENTORY_INCONSISTENCY',
                'Low Stock Products',
                f'{low_stock_count} products below minimum stock level',
                low_stock_count,
                0,
                'medium'
            ))

        return {
            'alert_count': len(alerts),
            'alerts': alerts,
            'critical_count': sum(1 for a in alerts if a['severity'] == 'critical'),
            'high_count': sum(1 for a in alerts if a['severity'] == 'high'),
            'generated_at': timezone.now().isoformat()
        }


class CachedIntelligenceAggregator:
    """
    Cached aggregator for operational intelligence.
    PERFORMANCE RULES:
    - All computations cached
    - No heavy DB aggregation per request
    - Use precomputed snapshots
    - No blocking operations
    - Safe under high traffic
    """

    @staticmethod
    def get_cache_key(scope: str) -> str:
        """Generate cache key for intelligence scope."""
        return f"{CACHE_PREFIX}{scope}"

    @classmethod
    def get_cached_intelligence(cls, scope: str = 'core') -> dict:
        """Get cached intelligence or compute fresh."""
        cache_key = cls.get_cache_key(scope)
        cached = cache.get(cache_key)

        if cached:
            cached['from_cache'] = True
            cached['cache_hit'] = True
            return cached

        intelligence = cls.compute_intelligence(scope)
        intelligence['from_cache'] = False
        intelligence['cache_hit'] = False

        cache.set(cache_key, intelligence, INTELLIGENCE_CACHE_TTL)

        return intelligence

    @classmethod
    def compute_intelligence(cls, scope: str) -> dict:
        """Compute fresh intelligence based on scope."""
        from core.operations.api_observability import get_metrics

        metrics_data = get_metrics()
        now = timezone.now()

        baseline_metrics = {
            'api_uptime_percent': 99.9,
            'response_time_ms': getattr(metrics_data, 'avg_response_time', 200),
            'error_rate_percent': getattr(metrics_data, 'error_rate', 0.5),
            'memory_percent': 60,
            'disk_percent': 50,
            'api_requests_history': getattr(metrics_data, 'request_count_history', []),
            'db_size_history': [],
            'storage_history': [],
            'unbalanced_entries': 0,
            'low_stock_products': 0,
            'latency_trend': 'stable',
            'error_trend': 'stable'
        }

        intelligence = {
            'sla_monitoring': SLAMonitoringEngine.calculate_compliance_score(baseline_metrics),
            'capacity_forecast': CapacityForecastEngine.forecast_capacity(baseline_metrics),
            'alerts': IntelligenceAlertSystem.analyze_and_generate_alerts(baseline_metrics, {}),
            'scope': scope,
            'generated_at': now.isoformat(),
            'expires_at': (now + timedelta(seconds=INTELLIGENCE_CACHE_TTL)).isoformat()
        }

        return intelligence

    @classmethod
    def invalidate_cache(cls, scope: str = 'core'):
        """Manually invalidate cache."""
        cache_key = cls.get_cache_key(scope)
        cache.delete(cache_key)

    @classmethod
    def get_all_intelligence(cls) -> dict:
        """Get complete operational intelligence with caching."""
        return cls.get_cached_intelligence('core')