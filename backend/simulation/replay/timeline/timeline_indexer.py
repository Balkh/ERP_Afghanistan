"""Timeline indexer — indexes timeline events for efficient lookup."""
from collections import deque, defaultdict
from typing import Any, Dict, List, Optional


class TimelineIndexer:
    def __init__(self, max_index_size: int = 500):
        self._by_tick: Dict[int, List[str]] = defaultdict(list)
        self._by_type: Dict[str, List[str]] = defaultdict(list)
        self._by_source: Dict[str, List[str]] = defaultdict(list)
        self._index_history: deque = deque(maxlen=max_index_size)

    def index_event(self, event_id: str, tick: int, event_type: str, source: str):
        self._by_tick[tick].append(event_id)
        self._by_type[event_type].append(event_id)
        self._by_source[source].append(event_id)
        self._index_history.append({
            'event_id': event_id, 'tick': tick,
        })

    def get_events_by_tick(self, tick: int) -> List[str]:
        return list(self._by_tick.get(tick, []))

    def get_events_by_type(self, event_type: str) -> List[str]:
        return list(self._by_type.get(event_type, []))

    def get_events_by_source(self, source: str) -> List[str]:
        return list(self._by_source.get(source, []))

    def get_tick_range(self, start: int, end: int) -> List[str]:
        result = []
        for tick in range(start, end + 1):
            result.extend(self._by_tick.get(tick, []))
        return result

    def clear(self):
        self._by_tick.clear()
        self._by_type.clear()
        self._by_source.clear()
        self._index_history.clear()
