from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseScenario(ABC):

    def __init__(self, name: str, scenario_type: str, config: Optional[Dict[str, Any]] = None) -> None:
        self._name = name
        self._scenario_type = scenario_type
        self._config = dict(config) if config else {}
        self._collected_state: Dict[str, Any] = {}

    @abstractmethod
    def setup(self, engine: Any) -> None:
        ...

    @abstractmethod
    def execute(self, engine: Any) -> Dict[str, Any]:
        ...

    @abstractmethod
    def teardown(self, engine: Any) -> Dict[str, Any]:
        ...

    def verify(self, integrity_matrix: Any) -> Dict[str, Any]:
        try:
            result = integrity_matrix.validate_all(self._collected_state)
            checks = result.get("checks", []) if isinstance(result, dict) else []
            violations = result.get("violations", []) if isinstance(result, dict) else []
            return {
                "passed": len(violations) == 0,
                "checks": list(checks),
                "violations": list(violations),
            }
        except Exception:
            return {
                "passed": False,
                "checks": [],
                "violations": [{"error": "integrity_matrix validation failed"}],
            }

    def get_name(self) -> str:
        return self._name

    def get_type(self) -> str:
        return self._scenario_type
