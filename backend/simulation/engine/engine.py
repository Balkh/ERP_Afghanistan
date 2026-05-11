import logging
import time
from typing import Any, Dict, List, Optional

from simulation.clocks.clock import VirtualClock
from simulation.events.bus import SimulationEventBus
from simulation.metrics.collector import SimulationMetricsCollector
from simulation.scheduler.scheduler import SimulationScheduler
from simulation.context.context import SimulationContext
from simulation.agents.agent import SimulationAgent
from simulation.agents.registry.registry import AgentRegistry
from simulation.agents.runtime.runtime import AgentRuntime
from simulation.workflows.orchestrator.orchestrator import WorkflowOrchestrator
from simulation.workflows.policies.policies import SimulationPolicyEngine
from simulation.truth_engine.engine import TruthEngine


logger = logging.getLogger('erp.simulation.engine')


class SimulationEngine:
    """
    Deterministic ERP simulation engine.
    Manages lifecycle, execution loop, agent/scenario registration.
    Isolated from production business logic.
    """

    STATE_CREATED = 'created'
    STATE_INITIALIZED = 'initialized'
    STATE_RUNNING = 'running'
    STATE_STOPPED = 'stopped'
    STATE_ERROR = 'error'

    def __init__(self, context: Optional[SimulationContext] = None,
                 config: Optional[dict] = None):
        self._config = dict(config) if config else {}
        self._context = context or SimulationContext(config=self._config)
        self._context.finalize()
        self._state = self.STATE_CREATED
        self._agents: Dict[str, SimulationAgent] = {}
        self._scenarios: Dict[str, Any] = {}
        self._max_ticks = self._config.get('max_ticks', 0)
        self._registry = AgentRegistry()
        self._runtime = AgentRuntime(self._context)
        self._orchestrator = WorkflowOrchestrator(self.event_bus)
        self._policy_engine = SimulationPolicyEngine()
        self._truth_engine: Optional[TruthEngine] = None
        if self._config.get('enable_truth_engine', False):
            logging.getLogger('erp.simulation.engine').info(
                "TruthEngine enabled"
            )
            self._truth_engine = TruthEngine(
                max_snapshots=self._config.get('truth_max_snapshots', 100)
            )

    @property
    def state(self) -> str:
        return self._state

    @property
    def context(self) -> SimulationContext:
        return self._context

    @property
    def clock(self) -> VirtualClock:
        return self._context.clock

    @property
    def event_bus(self) -> SimulationEventBus:
        return self._context.event_bus

    @property
    def metrics(self) -> SimulationMetricsCollector:
        return self._context.metrics

    @property
    def scheduler(self) -> SimulationScheduler:
        return self._context.scheduler

    @property
    def agents(self) -> Dict[str, SimulationAgent]:
        return dict(self._agents)

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    @property
    def runtime(self) -> AgentRuntime:
        return self._runtime

    @property
    def orchestrator(self) -> WorkflowOrchestrator:
        return self._orchestrator

    @property
    def policy_engine(self) -> SimulationPolicyEngine:
        return self._policy_engine

    @property
    def truth_engine(self) -> Optional[TruthEngine]:
        return self._truth_engine

    @truth_engine.setter
    def truth_engine(self, engine: TruthEngine):
        self._truth_engine = engine
        logger.info("TruthEngine attached to SimulationEngine")

    def initialize(self):
        if self._state not in (self.STATE_CREATED, self.STATE_STOPPED):
            raise RuntimeError(
                f"Cannot initialize from state '{self._state}'"
            )
        logger.info("SimulationEngine initializing...")
        for agent in self._agents.values():
            agent.initialize(self._context)
            schedules = agent.get_schedule()
            for schedule in schedules:
                sched_type = schedule.get('type', 'recurring')
                interval = schedule.get('interval_minutes', 10)
                delay = schedule.get('delay_minutes', 1)
                if sched_type == 'one_time':
                    self.scheduler.one_time(
                        agent.safe_execute, delay,
                        action_type=f"agent:{agent.agent_id}",
                    )
                else:
                    self.scheduler.recurring(
                        agent.safe_execute, interval,
                        action_type=f"agent:{agent.agent_id}",
                    )
        self._state = self.STATE_INITIALIZED
        logger.info("SimulationEngine initialized (%d agents)",
                     len(self._agents))

    def start(self):
        if self._state != self.STATE_INITIALIZED:
            self.initialize()
        self.clock.start()
        self._state = self.STATE_RUNNING
        self.event_bus.publish(
            'simulation_started', self.clock.now(),
            {'tick_interval_minutes':
             self.clock.tick_interval.total_seconds() / 60},
        )
        logger.info("SimulationEngine started at %s", self.clock.now())

    def stop(self):
        self.clock.stop()
        self._state = self.STATE_STOPPED
        self.event_bus.publish(
            'simulation_stopped', self.clock.now(),
            {'tick_count': self.clock.tick_count},
        )
        for agent in self._agents.values():
            agent.shutdown()
        logger.info("SimulationEngine stopped (%d ticks)",
                     self.clock.tick_count)

    def execute_registered_agents(self) -> List[Dict[str, Any]]:
        if not self._agents:
            return []
        return self._runtime.execute_all(self._agents)

    def run_agent_cycle(self) -> Dict[str, Any]:
        self.clock.tick()
        results = self.execute_registered_agents()
        return {
            'tick': self.clock.tick_count,
            'timestamp': self.clock.now(),
            'agents_executed': len(results),
            'results': results,
        }

    def execute_tick(self) -> Dict[str, Any]:
        if self._state != self.STATE_RUNNING:
            raise RuntimeError(
                f"Cannot execute tick from state '{self._state}'"
            )
        start_ts = time.monotonic()
        self.clock.tick()
        now = self.clock.now()
        executed_actions = self.scheduler.execute_due()
        elapsed = time.monotonic() - start_ts
        self.metrics.increment('ticks_executed')
        self.metrics.record_latency('tick', elapsed)
        self.event_bus.publish(
            'tick_executed', now,
            {'tick': self.clock.tick_count,
             'actions': len(executed_actions),
             'latency_seconds': elapsed},
        )
        if self._truth_engine is not None:
            self._run_truth_verification(now)
        return {
            'tick': self.clock.tick_count,
            'timestamp': now,
            'actions_executed': executed_actions,
            'latency_seconds': elapsed,
        }

    def run(self, max_ticks: Optional[int] = None) -> Dict[str, Any]:
        self.start()
        limit = max_ticks or self._max_ticks
        if limit <= 0:
            raise ValueError(
                "run() requires max_ticks > 0; use execute_tick() for "
                "manual control"
            )
        results = []
        for _ in range(limit):
            if self._state != self.STATE_RUNNING:
                break
            result = self.execute_tick()
            results.append(result)
        self.stop()
        return {
            'ticks_executed': self.clock.tick_count,
            'total_latency': sum(
                r['latency_seconds'] for r in results
            ),
            'results': results,
        }

    def register_agent(self, agent: SimulationAgent):
        if self._state not in (self.STATE_CREATED, self.STATE_STOPPED):
            raise RuntimeError(
                "Cannot register agent after initialization"
            )
        self._agents[agent.agent_id] = agent
        self.event_bus.publish(
            'agent_registered', self.clock.now(),
            {'agent_id': agent.agent_id, 'name': agent.name},
        )
        logger.debug("Agent '%s' registered", agent.agent_id)

    def register_scenario(self, scenario_id: str, scenario_data: Any):
        self._scenarios[scenario_id] = scenario_data
        self.event_bus.publish(
            'scenario_registered', self.clock.now(),
            {'scenario_id': scenario_id},
        )

    def collect_metrics(self) -> Dict[str, Any]:
        return self.metrics.snapshot()

    def _run_truth_verification(self, now):
        """Passive truth verification after each tick."""
        try:
            agent_executions = {}
            for aid, agent in self._agents.items():
                agent_executions[aid] = getattr(agent, 'execution_count', 0)
            workflow_completions = self._orchestrator.workflow_completions
            scenario_id = (
                next(iter(self._scenarios.keys()))
                if self._scenarios else 'default'
            )
            report = self._truth_engine.verify(
                scenario_id=scenario_id,
                tick=self.clock.tick_count,
                timestamp=now,
                event_history=self.event_bus.history,
                workflow_completions=workflow_completions,
                agent_executions=agent_executions,
            )
            mismatch_count = report.get('summary', {}).get(
                'total_mismatches', 0
            )
            if mismatch_count > 0:
                logger.warning(
                    "TruthEngine: %d mismatches at tick %d",
                    mismatch_count, self.clock.tick_count,
                )
        except Exception:
            logger.exception(
                "TruthEngine verification failed at tick %d",
                self.clock.tick_count,
            )

    def reset(self):
        for agent in self._agents.values():
            agent.shutdown()
        self._context.reset()
        self._context.finalize()
        self._state = self.STATE_CREATED
        self._agents.clear()
        self._scenarios.clear()
        self._truth_engine = None
        logger.info("SimulationEngine reset")
