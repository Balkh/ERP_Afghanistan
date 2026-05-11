import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


logger = logging.getLogger('erp.simulation.agent')


class SimulationAgent(ABC):
    """
    Abstract base contract for simulation agents.
    No AI logic. No autonomous reasoning. No random behavior.
    Deterministic execution contract only.
    """

    def __init__(self, agent_id: str, name: str):
        self._agent_id = agent_id
        self._name = name
        self._context = None
        self._initialized = False

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def context(self):
        return self._context

    @abstractmethod
    def initialize(self, context) -> None:
        """Initialize agent with simulation context."""

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """Execute one simulation step. Return result dict."""

    @abstractmethod
    def get_schedule(self) -> List[Dict[str, Any]]:
        """
        Return schedule definitions.
        Each entry: {'type': 'recurring'|'one_time',
                     'interval_minutes': int,
                     'delay_minutes': int}
        """

    @abstractmethod
    def validate(self) -> bool:
        """Validate agent internal state."""

    def shutdown(self):
        """Cleanup resources. Override in subclass if needed."""
        self._initialized = False
        logger.debug("Agent '%s' shutdown", self._agent_id)

    def safe_execute(self) -> Dict[str, Any]:
        """Wrapper that catches exceptions during execute()."""
        try:
            return self.execute()
        except Exception:
            logger.exception("Agent '%s' execute failed", self._agent_id)
            return {'status': 'error', 'agent_id': self._agent_id}
