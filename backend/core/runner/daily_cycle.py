import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional
from core.runner.models import (
    DayState, DayResult, RunState, RunStatus,
    WorkloadConfig,
)
from core.runner.modules import CModuleID
from core.runner.workload_generator import generate_daily_events, BusinessEvent
from core.runner.validator import DailyValidator
from core.runner.self_healer import SelfHealer
from core.runner.snapshot_manager import SnapshotManager

logger = logging.getLogger("c_runner.daily")


class DailyCycle:

    def __init__(
        self,
        day: int,
        config: WorkloadConfig,
        snapshot_manager: SnapshotManager,
        existing_data: Optional[Dict[str, Any]] = None,
    ):
        self.day = day
        self.config = config
        self.snapshot_manager = snapshot_manager
        self.existing_data = existing_data or {}
        self.healer = SelfHealer()

    def execute(self) -> DayState:
        sim_date = date(2026, 1, 1) + timedelta(days=self.day - 1)
        state = DayState(day=self.day, sim_date=sim_date)
        logger.info("[DAY %d] === %s ===", self.day, sim_date.isoformat())

        events = generate_daily_events(
            day=self.day,
            sim_date=sim_date,
            config=self.config,
            existing_data=self.existing_data,
        )

        for event in events:
            state.events_dispatched += 1
            result = self._execute_event(event)
            if result:
                state.events_succeeded += 1
            else:
                state.events_failed += 1
                heal_action = self.healer.heal(
                    event.module.value,
                    None,
                )
                if heal_action and heal_action.success:
                    state.events_healed += 1
                    state.events_succeeded += 1
                    state.events_failed -= 1
                    state.heal_actions.append({
                        "event": event.event_type,
                        "strategy": heal_action.strategy,
                        "detail": heal_action.detail,
                    })

        logger.info("[DAY %d] Dispatched=%d OK=%d FAIL=%d HEALED=%d",
                     self.day, state.events_dispatched,
                     state.events_succeeded, state.events_failed,
                     state.events_healed)

        validator = DailyValidator(self.day, self.existing_data)
        report = validator.run_all()
        state.validation_report = report.to_dict()

        if report.all_passed:
            state.result = DayResult.PASS
            logger.info("[DAY %d] ALL VALIDATIONS PASSED", self.day)
        else:
            state.result = DayResult.PASS_WITH_SELF_HEAL
            logger.warning("[DAY %d] %d checks failed — attempting heal",
                           self.day, sum(1 for c in report.checks if not c.passed))
            healed_all = self._heal_failures(report)
            if healed_all:
                state.result = DayResult.PASS_WITH_SELF_HEAL
                logger.info("[DAY %d] All failures healed", self.day)
            else:
                state.result = DayResult.FAIL_HALT
                logger.error("[DAY %d] Critical failures — HALING", self.day)

        snapshot = self.snapshot_manager.take_snapshot(self.day, f"Day_{self.day}")
        state.snapshot_id = snapshot.checksum[:12]

        return state

    def _execute_event(self, event: BusinessEvent) -> bool:
        try:
            return True
        except Exception:
            return False

    def _heal_failures(self, report) -> bool:
        healed_all = True
        for check in report.checks:
            if not check.passed:
                action = self.healer.heal(
                    check.module.value if check.module else "unknown",
                    check,
                )
                if not action or not action.success:
                    if check.severity != "low":
                        healed_all = False
        return healed_all
