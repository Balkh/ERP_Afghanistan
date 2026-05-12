"""Notification priority mapping for escalations."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import EscalationPriority


class NotificationPriorityMapper:
    PRIORITY_MAP = {
        EscalationPriority.IMMEDIATE: {'notify': True, 'channel': 'emergency',
                                        'max_delay_seconds': 0, 'requires_ack': True},
        EscalationPriority.HIGH: {'notify': True, 'channel': 'urgent',
                                   'max_delay_seconds': 60, 'requires_ack': True},
        EscalationPriority.MEDIUM: {'notify': True, 'channel': 'standard',
                                     'max_delay_seconds': 300, 'requires_ack': False},
        EscalationPriority.LOW: {'notify': False, 'channel': 'log',
                                  'max_delay_seconds': 3600, 'requires_ack': False},
    }

    def __init__(self, max_history: int = 200):
        self._mapping_history: deque = deque(maxlen=max_history)

    def map_priority(self, priority: EscalationPriority) -> Dict[str, Any]:
        result = dict(self.PRIORITY_MAP.get(priority, self.PRIORITY_MAP[EscalationPriority.LOW]))
        result['priority'] = priority.value
        self._mapping_history.append(result)
        return result

    def map_priority_str(self, priority_str: str) -> Dict[str, Any]:
        try:
            priority = EscalationPriority(priority_str)
        except ValueError:
            priority = EscalationPriority.LOW
        return self.map_priority(priority)

    def clear(self):
        self._mapping_history.clear()
