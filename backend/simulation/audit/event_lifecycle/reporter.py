"""
Task A: EventTopologyReport — generates structured reports on event topology.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger('erp.simulation.audit.event_lifecycle.reporter')


class EventTopologyReporter:
    def generate(self, analysis: Dict[str, Any],
                 retention: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'event_lifecycle_health': {
                'total_events': analysis.get('total_events', 0),
                'unique_types': analysis.get('unique_types', 0),
            },
            'retention_status': {
                'compliant': retention.get('retention_compliant', False),
                'actual_count': retention.get('actual_event_count', 0),
                'max_setting': retention.get('max_history_setting', 0),
            },
            'anomalies': {
                'orphan_events': analysis.get('orphan_events', 0),
                'duplicate_propagations': len(
                    analysis.get('duplicate_propagations', [])
                ),
                'recursion_risks': analysis.get('recursion_risks', []),
                'unconsumed_buildup': analysis.get('unconsumed_buildup', {}),
                'fan_out_chains': analysis.get('fan_out_chains', []),
                'longest_chain': analysis.get('longest_chain', 0),
            },
            'health_summary': self._compute_health(analysis, retention),
        }

    def _compute_health(self, analysis: Dict[str, Any],
                        retention: Dict[str, Any]) -> str:
        orphan = analysis.get('orphan_events', 0)
        dupes = len(analysis.get('duplicate_propagations', []))
        risks = len(analysis.get('recursion_risks', []))
        leak = retention.get('retention_leak_detected', False)
        if leak or orphan > 10 or dupes > 5:
            return 'CRITICAL'
        if orphan > 0 or dupes > 0 or risks > 0:
            return 'WARNING'
        return 'HEALTHY'
