import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from core.runner.models import (
    RunState, RunStatus, DayResult, DayState, WorkloadConfig,
)
from core.runner.daily_cycle import DailyCycle
from core.runner.snapshot_manager import SnapshotManager
from core.runner.modules import MODULE_REGISTRY, validate_module_dag, get_execution_order

logger = logging.getLogger("c_runner.engine")


class CRunnerEngine:

    _instance = None

    def __init__(self):
        self.state: RunState = RunState()
        self.snapshot_manager = SnapshotManager()

    @classmethod
    def get_instance(cls) -> "CRunnerEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(
        self,
        start_day: int = 1,
        end_day: int = 60,
        seed: int = 42,
        daily_sales_min: int = 3,
        daily_sales_max: int = 15,
        **kwargs,
    ):
        cfg = WorkloadConfig(
            seed=seed,
            daily_sales_min=daily_sales_min,
            daily_sales_max=daily_sales_max,
            **{k: v for k, v in kwargs.items()
               if hasattr(WorkloadConfig, k)},
        )
        self.state.config = cfg
        self.state.start_day = start_day
        self.state.end_day = end_day

    def validate_architecture(self) -> Dict[str, Any]:
        dag_errors = validate_module_dag()
        exec_order = get_execution_order()
        return {
            "dag_valid": len(dag_errors) == 0,
            "dag_errors": dag_errors,
            "module_count": len(MODULE_REGISTRY),
            "execution_order": [m.value for m in exec_order],
            "modules": {
                m.value: {
                    "label": mod.label,
                    "app": mod.django_app,
                    "requires": [r.value for r in mod.requires],
                }
                for m, mod in MODULE_REGISTRY.items()
            },
        }

    def run(self, existing_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.state.run_id = str(uuid.uuid4())[:8]
        self.state.status = RunStatus.RUNNING
        self.state.start_time = datetime.utcnow().isoformat()
        existing_data = existing_data or {}

        logger.info("[C-RUNNER] === STARTING 60-DAY SIMULATION ===")
        logger.info("[C-RUNNER] Run ID: %s", self.state.run_id)
        logger.info("[C-RUNNER] Modules: %d (%s)",
                     len(MODULE_REGISTRY),
                     ", ".join(m.value for m in MODULE_REGISTRY))

        for day in range(self.state.start_day, self.state.end_day + 1):
            self.state.current_day = day

            cycle = DailyCycle(
                day=day,
                config=self.state.config,
                snapshot_manager=self.snapshot_manager,
                existing_data=existing_data,
            )
            day_state = cycle.execute()
            self.state.days[day] = day_state

            self.state.total_events_dispatched += day_state.events_dispatched
            self.state.total_events_succeeded += day_state.events_succeeded
            self.state.total_events_failed += day_state.events_failed
            self.state.total_events_healed += day_state.events_healed

            if day_state.result == DayResult.FAIL_HALT:
                logger.error("[C-RUNNER] Day %d: CRITICAL FAILURE — HALTING", day)
                self.state.status = RunStatus.HALTED
                break

            if day_state.result == DayResult.FAIL_ISOLATE:
                logger.warning("[C-RUNNER] Day %d: ISOLATION TRIGGERED — continuing", day)

        self._finalize()
        return self.get_report()

    def _finalize(self):
        self.state.end_time = datetime.utcnow().isoformat()
        days_completed = len(self.state.days)
        all_passed = all(
            ds.result in (DayResult.PASS, DayResult.PASS_WITH_SELF_HEAL)
            for ds in self.state.days.values()
        )
        if self.state.status == RunStatus.HALTED:
            self.state.final_verdict = "HALTED_EARLY"
        elif all_passed and days_completed >= self.state.end_day:
            self.state.status = RunStatus.COMPLETED
            self.state.final_verdict = "SIMULATION_COMPLETE_ALL_PASS"
        elif all_passed:
            self.state.status = RunStatus.COMPLETED
            self.state.final_verdict = "SIMULATION_PARTIAL_ALL_PASS"
        else:
            self.state.status = RunStatus.FAILED
            self.state.final_verdict = "SIMULATION_FAILED"

    def get_report(self) -> Dict[str, Any]:
        return {
            "run_id": self.state.run_id,
            "status": self.state.status.name,
            "verdict": self.state.final_verdict,
            "start_day": self.state.start_day,
            "end_day": self.state.end_day,
            "days_completed": len(self.state.days),
            "start_time": self.state.start_time,
            "end_time": self.state.end_time,
            "stats": {
                "events_dispatched": self.state.total_events_dispatched,
                "events_succeeded": self.state.total_events_succeeded,
                "events_failed": self.state.total_events_failed,
                "events_healed": self.state.total_events_healed,
                "snapshots": len(self.snapshot_manager.list_snapshots()),
            },
            "results": {
                str(d): self._day_result_to_str(ds)
                for d, ds in self.state.days.items()
            },
            "module_arch": self.validate_architecture(),
        }

    def _day_result_to_str(self, ds: DayState) -> Dict[str, Any]:
        return {
            "date": ds.sim_date.isoformat(),
            "result": ds.result.name if ds.result else "NONE",
            "events": {
                "dispatched": ds.events_dispatched,
                "succeeded": ds.events_succeeded,
                "failed": ds.events_failed,
                "healed": ds.events_healed,
            },
            "snapshot": ds.snapshot_id,
            "validations": ds.validation_report,
        }
