import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger('erp.simulation.event_bus')


EventPayload = Dict[str, Any]
EventHandler = Callable[['SimulationEvent'], None]


class SimulationEvent:
    """Immutable simulation event."""

    __slots__ = ('id', 'type', 'timestamp', 'payload')

    def __init__(self, event_type: str, timestamp: datetime,
                 payload: Optional[EventPayload] = None):
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.timestamp = timestamp
        self.payload = dict(payload) if payload else {}

    def __repr__(self) -> str:
        return f"SimulationEvent(type={self.type}, ts={self.timestamp})"


class SimulationEventBus:
    """
    Publish-subscribe event bus for simulation.
    Bounded memory. Exception-isolated subscribers. Immutable events.
    """

    VALID_EVENT_TYPES = [
        'simulation_started',
        'simulation_stopped',
        'tick_executed',
        'action_executed',
        'action_failed',
        'metric_recorded',
        'agent_registered',
        'agent_initialized',
        'agent_executed',
        'agent_failed',
        'scenario_registered',
        'schedule_triggered',
        'schedule_cancelled',
        'workflow_started',
        'workflow_completed',
        'workflow_failed',
        'return_initiated',
    ]

    def __init__(self, max_history: int = 10000):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: deque = deque(maxlen=max_history)
        self._max_history = max_history

    @property
    def history(self) -> List[SimulationEvent]:
        return list(self._history)

    @property
    def event_count(self) -> int:
        return len(self._history)

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event_type: str, timestamp: datetime,
                payload: Optional[EventPayload] = None):
        event = SimulationEvent(event_type, timestamp, payload)
        self._history.append(event)
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "EventBus: handler failed for event '%s' "
                    "(handler=%s)", event_type,
                    getattr(handler, '__name__', str(handler))
                )

    def clear(self):
        self._history.clear()
        self._subscribers.clear()

    def events_by_type(self, event_type: str) -> List[SimulationEvent]:
        return [e for e in self._history if e.type == event_type]
