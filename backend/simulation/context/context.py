import logging
from typing import Optional

from simulation.clocks.clock import VirtualClock
from simulation.events.bus import SimulationEventBus
from simulation.metrics.collector import SimulationMetricsCollector
from simulation.scheduler.scheduler import SimulationScheduler


logger = logging.getLogger('erp.simulation.context')


class SimulationContext:
    """
    Controlled access to simulation shared state.
    Immutable after construction. No uncontrolled global state.
    Clear lifecycle ownership.
    """

    def __init__(
        self,
        clock: Optional[VirtualClock] = None,
        event_bus: Optional[SimulationEventBus] = None,
        metrics: Optional[SimulationMetricsCollector] = None,
        scheduler: Optional[SimulationScheduler] = None,
        config: Optional[dict] = None,
    ):
        self._clock = clock or VirtualClock()
        self._event_bus = event_bus or SimulationEventBus()
        self._metrics = metrics or SimulationMetricsCollector()
        self._scheduler = scheduler or SimulationScheduler(
            clock=self._clock,
            event_bus=self._event_bus,
        )
        self._config = dict(config) if config else {}
        self._finalized = False

    def finalize(self):
        """Prevent further modification."""
        self._finalized = True
        logger.debug("SimulationContext finalized")

    @property
    def clock(self) -> VirtualClock:
        return self._clock

    @property
    def event_bus(self) -> SimulationEventBus:
        return self._event_bus

    @property
    def metrics(self) -> SimulationMetricsCollector:
        return self._metrics

    @property
    def scheduler(self) -> SimulationScheduler:
        return self._scheduler

    @property
    def config(self) -> dict:
        return dict(self._config)

    def reset(self):
        self._clock.reset()
        self._event_bus.clear()
        self._metrics.reset()
        self._scheduler.clear()
        self._finalized = False
        logger.debug("SimulationContext reset")
