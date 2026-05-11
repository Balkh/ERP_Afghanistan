import logging
from datetime import datetime, timedelta
from typing import Optional


logger = logging.getLogger('erp.simulation.virtual_clock')


class VirtualClock:
    """
    Deterministic simulated clock.
    No dependency on wall-clock execution speed.
    """

    def __init__(self, start_datetime: Optional[datetime] = None,
                 tick_interval_minutes: int = 1):
        self._tick_interval = timedelta(minutes=tick_interval_minutes)
        self._start_time = start_datetime or datetime(2024, 1, 1, 0, 0, 0)
        self._current_time = self._start_time
        self._tick_count = 0
        self._running = False

    @property
    def tick_interval(self) -> timedelta:
        return self._tick_interval

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        self._running = True
        logger.debug("VirtualClock started at %s", self._current_time)

    def stop(self):
        self._running = False
        logger.debug("VirtualClock stopped at tick %d", self._tick_count)

    def now(self) -> datetime:
        return self._current_time

    def tick(self) -> datetime:
        if not self._running:
            self.start()
        self._current_time += self._tick_interval
        self._tick_count += 1
        return self._current_time

    def advance(self, minutes: int) -> datetime:
        if minutes < 0:
            raise ValueError("Cannot advance negative minutes")
        self._current_time += timedelta(minutes=minutes)
        self._tick_count += 1
        return self._current_time

    def reset(self):
        self._current_time = self._start_time
        self._tick_count = 0
        self._running = False
        logger.debug("VirtualClock reset to %s", self._start_time)

    def elapsed(self) -> timedelta:
        return self._current_time - self._start_time

    def set_time(self, dt: datetime):
        self._current_time = dt
