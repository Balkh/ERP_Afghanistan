"""
Phase 5B.7 — Workflow Context & Router Engine.

Provides cross-module state propagation, step-by-step navigation,
persistent workflow state, and audit trail per workflow.

All screens use WorkflowContext to share selected entities
(event_id, decision_id, approval_id, aggregate_id, etc.)
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class WorkflowStep:
    """A single step in a workflow navigation sequence."""
    screen_id: str = ""
    screen_title: str = ""
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    entered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class WorkflowContext:
    """Shared context propagated across screens during a workflow.

    This is the SINGLE source of cross-module state.
    Every screen reads from and writes to this context.
    """
    workflow_id: str = field(default_factory=lambda: f"wf_{uuid4().hex[:8]}")
    workflow_type: str = ""

    # Selected entities
    selected_event_id: str = ""
    selected_decision_id: str = ""
    selected_approval_id: str = ""
    selected_aggregate_id: str = ""
    selected_domain: str = ""
    selected_trace_id: str = ""
    selected_anomaly_id: str = ""

    # Investigation state
    trace_chain: List[str] = field(default_factory=list)
    causation_graph: Dict[str, Any] = field(default_factory=dict)

    # Navigation history
    navigation_history: List[WorkflowStep] = field(default_factory=list)

    # Persistent workflow metadata
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def push_step(self, screen_id: str, screen_title: str = ""):
        self.navigation_history.append(WorkflowStep(
            screen_id=screen_id,
            screen_title=screen_title,
            context_snapshot={
                "event_id": self.selected_event_id,
                "decision_id": self.selected_decision_id,
                "approval_id": self.selected_approval_id,
                "aggregate_id": self.selected_aggregate_id,
                "domain": self.selected_domain,
            },
        ))
        self.last_activity = datetime.utcnow().isoformat() + "Z"

    def pop_step(self) -> Optional[WorkflowStep]:
        if self.navigation_history:
            step = self.navigation_history.pop()
            if self.navigation_history:
                prev = self.navigation_history[-1]
                self.restore(prev.context_snapshot)
            return step
        return None

    def restore(self, snapshot: Dict[str, Any]):
        self.selected_event_id = snapshot.get("event_id", self.selected_event_id)
        self.selected_decision_id = snapshot.get("decision_id", self.selected_decision_id)
        self.selected_approval_id = snapshot.get("approval_id", self.selected_approval_id)
        self.selected_aggregate_id = snapshot.get("aggregate_id", self.selected_aggregate_id)
        self.selected_domain = snapshot.get("domain", self.selected_domain)

    def set_event(self, event_id: str, domain: str = "", aggregate_id: str = ""):
        self.selected_event_id = event_id
        if domain: self.selected_domain = domain
        if aggregate_id: self.selected_aggregate_id = aggregate_id

    def set_decision(self, decision_id: str):
        self.selected_decision_id = decision_id

    def set_approval(self, approval_id: str):
        self.selected_approval_id = approval_id

    def set_anomaly(self, anomaly_id: str, domain: str = ""):
        self.selected_anomaly_id = anomaly_id
        if domain: self.selected_domain = domain

    def add_to_trace(self, event_id: str):
        if event_id not in self.trace_chain:
            self.trace_chain.append(event_id)

    def get_workflow_summary(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "steps": len(self.navigation_history),
            "current_screen": self.navigation_history[-1].screen_id
            if self.navigation_history else "",
            "selected_event": self.selected_event_id,
            "selected_decision": self.selected_decision_id,
            "selected_approval": self.selected_approval_id,
            "trace_length": len(self.trace_chain),
            "started_at": self.started_at,
            "last_activity": self.last_activity,
        }


class WorkflowRouter:
    """Routes between screens with context propagation.

    Manages step-by-step navigation, backtracking, and
    persistent workflow state across the Control Tower.
    """

    def __init__(self):
        self._context = WorkflowContext()
        self._listeners: Dict[str, List[Callable]] = {}
        self._screen_registry: Dict[str, str] = {}

    def register_screen(self, screen_id: str, title: str = ""):
        self._screen_registry[screen_id] = title or screen_id

    def start_workflow(self, workflow_type: str, initial_screen: str = ""):
        self._context = WorkflowContext(workflow_type=workflow_type)
        if initial_screen:
            self.navigate_to(initial_screen)
        self._emit("workflow_started", self._context)
        return self._context

    def navigate_to(self, screen_id: str):
        title = self._screen_registry.get(screen_id, screen_id)
        self._context.push_step(screen_id, title)
        self._emit("navigation", {"from": self._get_previous(), "to": screen_id})
        return self._context

    def go_back(self):
        step = self._context.pop_step()
        if step:
            self._emit("navigation_back", step)
        return self._context

    def get_context(self) -> WorkflowContext:
        return self._context

    def reset_context(self):
        self._context = WorkflowContext()

    def on(self, event: str, callback: Callable):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def _emit(self, event: str, data: Any):
        for cb in self._listeners.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    def _get_previous(self) -> str:
        if len(self._context.navigation_history) >= 2:
            return self._context.navigation_history[-2].screen_id
        return ""


# Global singleton
_router: Optional[WorkflowRouter] = None


def get_router() -> WorkflowRouter:
    global _router
    if _router is None:
        _router = WorkflowRouter()
        _register_default_screens(_router)
    return _router


def _register_default_screens(router: WorkflowRouter):
        screens = {
            "control_tower": "Control Tower",
            "workflow_execution": "Workflow Execution",
            "event_investigation": "Event Investigation",
            "anomaly_investigation": "Anomaly Investigation",
            "financial_control_tower": "Financial Control Tower",
            "system_health": "System Health Overview",
            "approval_workflow": "Approval Workflows",
            "event_store": "Event Store",
            "trace_viewer": "Trace Viewer",
            "timeline_viewer": "Timeline Viewer",
            "drift_dashboard": "Drift Dashboard",
            "anomaly_dashboard": "Anomaly Dashboard",
            "forecast_dashboard": "Forecast Dashboard",
            "decision_options": "Decision Options",
            "anomaly_warning_center": "Anomaly Warning Center",
            "master_dashboard": "Intelligence Dashboard",
            "replay_time_travel": "Replay Time-Travel",
            "cognitive_dashboard": "Enterprise Cognitive Dashboard",
            "causal_reasoning": "Causal Reasoning & WHY Analysis",
            "decision_intelligence": "Decision Intelligence Dashboard",
            "cash_flow": "Cash Flow Statement",
            "employee_summary": "Employee Summary",
            "attendance_report": "Attendance Report",
            "leave_report": "Leave Report",
            "overtime_report": "Overtime Report",
            "payroll_summary": "Payroll Summary",
            "payroll_trend": "Payroll Trend",
            "payroll_dept_cost": "Department Payroll Cost",
            "payroll_emp_history": "Employee Payroll History",
        }
        for sid, title in screens.items():
            router.register_screen(sid, title)
