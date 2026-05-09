"""
Signal Coordinator - Deduplication Layer for Operational Intelligence.

Phase 12.1 - Signal Governance:
- All signals MUST pass through SignalCoordinator before alert/dashboard display
- Deduplication rules: same signal_id within 10 min → suppress
- Same metric + same severity → merge into single signal
- Higher severity overrides lower severity
- Single source of truth for Control Center and Alerts

Architecture:
- Intelligence Layer = signal producer ONLY
- SignalCoordinator = single truth layer
- Control Center = signal consumer ONLY
- Alert System = formatted output ONLY
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from typing import Dict, List, Optional, Any


logger = logging.getLogger('erp.signal_coordinator')


class SignalCoordinator:
    """
    Centralized Signal Deduplication Layer.
    All signals must pass through this coordinator.
    """

    _instance = None
    _signal_store: Dict[str, dict] = {}
    _signal_history: List[dict] = []

    DEDUP_WINDOW_MINUTES = 10
    CACHE_PREFIX = 'signal_'
    CACHE_TTL = 600

    SEVERITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._load_from_cache()

    def _load_from_cache(self):
        cached_signals = cache.get(f'{self.CACHE_PREFIX}store')
        if cached_signals:
            self._signal_store = cached_signals

    def _save_to_cache(self):
        cache.set(f'{self.CACHE_PREFIX}store', self._signal_store, self.CACHE_TTL)

    def generate_signal_id(self, metric_name: str, rule_id: str, source: str) -> str:
        """Generate unique signal ID from components."""
        return f"{source}:{rule_id}:{metric_name}"

    def is_duplicate(self, signal_id: str) -> bool:
        """Check if signal with same ID exists within deduplication window."""
        if signal_id in self._signal_store:
            last_seen = self._signal_store[signal_id].get('last_seen')
            if last_seen:
                time_since_last = (timezone.now() - last_seen).total_seconds() / 60
                if time_since_last < self.DEDUP_WINDOW_MINUTES:
                    return True
        return False

    def get_existing_signal(self, signal_id: str) -> Optional[dict]:
        """Get existing signal if any."""
        return self._signal_store.get(signal_id)

    def should_override(self, new_severity: str, existing_severity: str) -> bool:
        """Check if new severity should override existing."""
        new_order = self.SEVERITY_ORDER.get(new_severity, 4)
        existing_order = self.SEVERITY_ORDER.get(existing_severity, 4)
        return new_order < existing_order

    def merge_signals(self, existing: dict, new: dict) -> dict:
        """Merge two signals with same metric + severity."""
        merged = existing.copy()

        merged['count'] = existing.get('count', 1) + 1
        merged['last_seen'] = timezone.now()
        merged['updated_at'] = timezone.now().isoformat()

        if 'values' not in merged:
            merged['values'] = [existing.get('value', 0)]
        merged['values'].append(new.get('value', 0))

        if new.get('more_severe', False):
            merged['severity'] = new['severity']
            merged['more_severe'] = True

        return merged

    def register_signal(self, signal: dict) -> dict:
        """
        Register a signal through the coordinator.
        Returns dict with 'accepted' bool and 'signal' or 'reason'.
        """
        metric_name = signal.get('metric_name', 'unknown')
        rule_id = signal.get('rule_id', 'unknown')
        source = signal.get('source', 'intelligence')
        severity = signal.get('severity', 'low')

        signal_id = self.generate_signal_id(metric_name, rule_id, source)

        if self.is_duplicate(signal_id):
            existing = self.get_existing_signal(signal_id)

            if self.should_override(severity, existing.get('severity', 'low')):
                self._signal_store[signal_id] = {
                    **signal,
                    'signal_id': signal_id,
                    'last_seen': timezone.now(),
                    'updated_at': timezone.now().isoformat(),
                    'overrode': True
                }
                self._save_to_cache()
                return {'accepted': True, 'signal': self._signal_store[signal_id], 'reason': 'overrode_lower_severity'}

            merged = self.merge_signals(existing, signal)
            self._signal_store[signal_id] = merged
            self._save_to_cache()
            return {'accepted': True, 'signal': merged, 'reason': 'merged'}

        self._signal_store[signal_id] = {
            **signal,
            'signal_id': signal_id,
            'first_seen': timezone.now(),
            'last_seen': timezone.now(),
            'created_at': timezone.now().isoformat(),
            'updated_at': timezone.now().isoformat(),
            'count': 1
        }
        self._save_to_cache()

        self._signal_history.append(signal_id)
        if len(self._signal_history) > 1000:
            self._signal_history = self._signal_history[-1000:]

        return {'accepted': True, 'signal': self._signal_store[signal_id], 'reason': 'new'}

    def get_active_signals(self, category: str = None, min_severity: str = None) -> List[dict]:
        """Get active signals, optionally filtered by category and minimum severity."""
        signals = list(self._signal_store.values())

        if category:
            signals = [s for s in signals if s.get('category') == category]

        if min_severity:
            min_order = self.SEVERITY_ORDER.get(min_severity, 4)
            signals = [s for s in signals if self.SEVERITY_ORDER.get(s.get('severity'), 4) <= min_order]

        return signals

    def get_signal_summary(self) -> dict:
        """Get summary of all active signals."""
        signals = list(self._signal_store.values())

        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        source_counts = defaultdict(int)

        for signal in signals:
            severity_counts[signal.get('severity', 'unknown')] += 1
            category_counts[signal.get('category', 'unknown')] += 1
            source_counts[signal.get('source', 'unknown')] += 1

        return {
            'total_active_signals': len(signals),
            'by_severity': dict(severity_counts),
            'by_category': dict(category_counts),
            'by_source': dict(source_counts),
            'dedup_window_minutes': self.DEDUP_WINDOW_MINUTES
        }

    def clear_signals(self, older_than_minutes: int = None):
        """Clear old signals from store."""
        if older_than_minutes is None:
            self._signal_store.clear()
            self._save_to_cache()
            return

        cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
        to_remove = []

        for signal_id, signal in self._signal_store.items():
            last_seen = signal.get('last_seen')
            if last_seen and last_seen < cutoff:
                to_remove.append(signal_id)

        for signal_id in to_remove:
            del self._signal_store[signal_id]

        if to_remove:
            self._save_to_cache()

    def acknowledge_signal(self, signal_id: str) -> bool:
        """Mark signal as acknowledged."""
        if signal_id in self._signal_store:
            self._signal_store[signal_id]['acknowledged'] = True
            self._signal_store[signal_id]['acknowledged_at'] = timezone.now().isoformat()
            self._save_to_cache()
            return True
        return False

    def get_unacknowledged_signals(self) -> List[dict]:
        """Get all unacknowledged signals."""
        return [
            s for s in self._signal_store.values()
            if not s.get('acknowledged', False)
        ]


def register_intelligence_signal(signal: dict) -> dict:
    """Public interface to register intelligence signals."""
    coordinator = SignalCoordinator.get_instance()
    return coordinator.register_signal(signal)


def get_active_signals(category: str = None, min_severity: str = None) -> List[dict]:
    """Public interface to get active signals."""
    coordinator = SignalCoordinator.get_instance()
    return coordinator.get_active_signals(category, min_severity)


def get_signal_summary() -> dict:
    """Public interface to get signal summary."""
    coordinator = SignalCoordinator.get_instance()
    return coordinator.get_signal_summary()


def clear_old_signals(older_than_minutes: int = 60):
    """Public interface to clear old signals."""
    coordinator = SignalCoordinator.get_instance()
    coordinator.clear_signals(older_than_minutes)