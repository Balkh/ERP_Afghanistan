"""
Phase 5B.6 — Governance API Client.

Provides typed access to:
- Decision pipeline (intercept, evaluate)
- Simulation sandbox
- Approval gateway (workflows, sign, escalate, cancel)
"""
from typing import Any, Dict, List, Optional
from api.client import APIClient


class GovernanceAPIClient:
    """Typed client for Governance API endpoints."""

    def __init__(self, client: APIClient):
        self._c = client
        self._base = "/api/v1/governance"

    # ─── Decision Pipeline ───

    def intercept(self, action_type: str, source: str = "ui",
                  context: dict = None, metadata: dict = None) -> dict:
        return self._c.post(f"{self._base}/intercept/", {
            "action_type": action_type, "source": source,
            "context": context or {}, "metadata": metadata or {},
        })

    def evaluate(self, action_type: str, source: str = "ui",
                 context: dict = None, metadata: dict = None) -> dict:
        return self._c.post(f"{self._base}/evaluate/", {
            "action_type": action_type, "source": source,
            "context": context or {}, "metadata": metadata or {},
        })

    def get_action_types(self) -> dict:
        return self._c.get(f"{self._base}/action-types/")

    # ─── Simulation ───

    def simulate(self, decision_result: dict) -> dict:
        return self._c.post(f"{self._base}/simulate/", {
            "decision_result": decision_result,
        })

    # ─── Approval Workflows ───

    def list_workflows(self) -> list:
        resp = self._c.get(f"{self._base}/workflows/")
        return resp.get("data", []) if isinstance(resp, dict) else resp

    def get_workflow(self, workflow_id: str) -> dict:
        return self._c.get(f"{self._base}/workflows/{workflow_id}/")

    def create_workflow(self, decision_result: dict,
                        simulation_plan: dict = None,
                        simulation_outcome: dict = None) -> dict:
        return self._c.post(f"{self._base}/workflows/create/", {
            "decision_result": decision_result,
            "simulation_plan": simulation_plan,
            "simulation_outcome": simulation_outcome,
        })

    def sign_workflow(self, workflow_id: str, approver_id: str,
                      authority_level: str, decision: str,
                      justification: str = "") -> dict:
        return self._c.post(f"{self._base}/workflows/{workflow_id}/sign/", {
            "approver_id": approver_id,
            "authority_level": authority_level,
            "decision": decision,
            "justification": justification,
        })

    def escalate_workflow(self, workflow_id: str, escalated_by: str,
                          escalated_to: str, reason: str) -> dict:
        return self._c.post(f"{self._base}/workflows/{workflow_id}/escalate/", {
            "escalated_by": escalated_by,
            "escalated_to": escalated_to,
            "reason": reason,
        })

    def cancel_workflow(self, workflow_id: str, cancelled_by: str) -> dict:
        return self._c.post(f"{self._base}/workflows/{workflow_id}/cancel/", {
            "cancelled_by": cancelled_by,
        })

    def get_gateway_status(self) -> dict:
        return self._c.get(f"{self._base}/status/")
