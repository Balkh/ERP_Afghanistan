import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger('erp.simulation.agent_registry')


class AgentRegistry:
    """
    Deterministic agent registration system.
    Stores agent metadata. Prevents duplicate registration.
    No execution logic. No scheduling logic.
    """

    def __init__(self):
        self._entries: Dict[str, dict] = {}
        self._order: List[str] = []

    def register(self, agent_type: str, agent_class: type,
                 metadata: Optional[dict] = None,
                 description: str = '') -> None:
        if agent_type in self._entries:
            raise ValueError(
                f"Agent type '{agent_type}' already registered"
            )
        self._entries[agent_type] = {
            'agent_type': agent_type,
            'class': agent_class,
            'metadata': dict(metadata) if metadata else {},
            'description': description,
        }
        self._order.append(agent_type)
        logger.debug("Registry: registered '%s'", agent_type)

    def get(self, agent_type: str) -> Optional[dict]:
        return self._entries.get(agent_type)

    def get_class(self, agent_type: str) -> Optional[type]:
        entry = self._entries.get(agent_type)
        return entry['class'] if entry else None

    def contains(self, agent_type: str) -> bool:
        return agent_type in self._entries

    @property
    def registered_types(self) -> List[str]:
        return list(self._order)

    @property
    def count(self) -> int:
        return len(self._entries)

    def get_all(self) -> Dict[str, dict]:
        return dict(self._entries)

    def unregister(self, agent_type: str) -> bool:
        if agent_type not in self._entries:
            return False
        del self._entries[agent_type]
        self._order = [t for t in self._order if t != agent_type]
        return True

    def clear(self):
        self._entries.clear()
        self._order.clear()
