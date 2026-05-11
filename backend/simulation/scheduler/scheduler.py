import heapq
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger('erp.simulation.scheduler')


@dataclass(order=True)
class ScheduledAction:
    next_run: datetime
    priority: int = 0
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ''
    callback: Callable = field(compare=False, default=lambda: None)
    interval_minutes: Optional[int] = field(compare=False, default=None)
    recurring: bool = field(compare=False, default=False)
    payload: dict = field(compare=False, default_factory=dict)
    cancelled: bool = field(compare=False, default=False)


class SimulationScheduler:
    """
    Deterministic scheduler for simulation actions.
    Heap-based ordering. No race conditions.
    Safe cancellation. Predictable recurring execution.
    """

    def __init__(self, clock, event_bus):
        self._clock = clock
        self._event_bus = event_bus
        self._queue: List[ScheduledAction] = []
        self._actions: Dict[str, ScheduledAction] = {}

    def _add_action(self, action: ScheduledAction):
        heapq.heappush(self._queue, action)
        self._actions[action.action_id] = action

    def one_time(self, callback: Callable, delay_minutes: int,
                 action_type: str = 'one_time',
                 payload: Optional[dict] = None) -> str:
        run_at = self._clock.now() + timedelta(minutes=delay_minutes)
        action = ScheduledAction(
            next_run=run_at,
            action_type=action_type,
            callback=callback,
            interval_minutes=None,
            recurring=False,
            payload=payload or {},
        )
        self._add_action(action)
        return action.action_id

    def recurring(self, callback: Callable, interval_minutes: int,
                  action_type: str = 'recurring',
                  payload: Optional[dict] = None) -> str:
        run_at = self._clock.now() + timedelta(minutes=interval_minutes)
        action = ScheduledAction(
            next_run=run_at,
            action_type=action_type,
            callback=callback,
            interval_minutes=interval_minutes,
            recurring=True,
            payload=payload or {},
        )
        self._add_action(action)
        return action.action_id

    def cancel(self, action_id: str) -> bool:
        action = self._actions.get(action_id)
        if action is None:
            return False
        action.cancelled = True
        self._event_bus.publish(
            'schedule_cancelled',
            self._clock.now(),
            {'action_id': action_id, 'action_type': action.action_type},
        )
        return True

    def execute_due(self) -> List[Dict[str, Any]]:
        now = self._clock.now()
        executed = []
        while self._queue and self._queue[0].next_run <= now:
            action = heapq.heappop(self._queue)
            if action.cancelled:
                continue
            try:
                if action.recurring and action.interval_minutes:
                    next_run = action.next_run + timedelta(
                        minutes=action.interval_minutes
                    )
                    new_action = ScheduledAction(
                        next_run=next_run,
                        priority=action.priority,
                        action_type=action.action_type,
                        callback=action.callback,
                        interval_minutes=action.interval_minutes,
                        recurring=True,
                        payload=action.payload,
                    )
                    self._add_action(new_action)
                action.callback()
                self._event_bus.publish(
                    'action_executed',
                    now,
                    {
                        'action_id': action.action_id,
                        'action_type': action.action_type,
                        'recurring': action.recurring,
                    },
                )
                executed.append({
                    'action_id': action.action_id,
                    'action_type': action.action_type,
                    'status': 'executed',
                })
            except Exception:
                logger.exception(
                    "Scheduler: action '%s' failed", action.action_id
                )
                self._event_bus.publish(
                    'action_failed',
                    now,
                    {
                        'action_id': action.action_id,
                        'action_type': action.action_type,
                    },
                )
                executed.append({
                    'action_id': action.action_id,
                    'action_type': action.action_type,
                    'status': 'failed',
                })
        return executed

    @property
    def pending_count(self) -> int:
        return len([a for a in self._queue if not a.cancelled])

    @property
    def actions(self) -> Dict[str, ScheduledAction]:
        return dict(self._actions)

    def clear(self):
        self._queue.clear()
        self._actions.clear()
