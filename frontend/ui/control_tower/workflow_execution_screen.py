"""
Phase 5B.7 — Workflow Execution Screen.

Step-by-step Decision → Approval → Event → Truth → Observability → Intelligence flow.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTextEdit, QLineEdit,
                                 QComboBox, QGroupBox, QSplitter, QTableWidget,
                                 QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from api.client import APIClient
from api.governance_client import GovernanceAPIClient
from api.truth_client import TruthAPIClient
from api.observability_client import ObservabilityAPIClient
from ui.control_tower.workflow_engine import get_router
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE)


class WorkflowExecutionScreen(QWidget):
    """Decision → Approval → Event → Truth → Observability → Intelligence flow."""

    STEPS = ["Decision", "Approval", "Event", "Truth Verification", "Observability Trace", "Intelligence Insight"]

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = api_client or APIClient()
        self._gov = GovernanceAPIClient(self._api)
        self._truth = TruthAPIClient(self._api)
        self._obs = ObservabilityAPIClient(self._api)
        self._router = get_router()
        self._current_step = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QLabel("Workflow Execution: Decision → Approval → Execute")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        # Step indicator
        self.step_label = QLabel("Step 1/6: Decision")
        self.step_label.setFont(QFont("Segoe UI", 14))
        self.step_label.setStyleSheet(f"color: {COLOR_INFO};")
        layout.addWidget(self.step_label)

        # Progress bar (text-based)
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self.progress_label)

        # Main content
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setStyleSheet(f"""
            QTextEdit {{ background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 12px;
            font-family: 'Consolas', monospace; font-size: 12px; }}
        """)
        self.content.setMinimumHeight(200)
        layout.addWidget(self.content)

        # Action area
        action_group = QGroupBox("Action")
        action_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; font-weight: bold;
            border: 1px solid {COLOR_BORDER}; border-radius: 6px; margin-top: 8px; padding-top: 16px; }}
        """)
        action_layout = QVBoxLayout(action_group)

        self.action_input = QLineEdit()
        self.action_input.setPlaceholderText("Enter action type (e.g., inventory_dispatch)...")
        self.action_input.setStyleSheet(f"""
            QLineEdit {{ background: {COLOR_BG_MAIN}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 8px; }}
        """)
        action_layout.addWidget(self.action_input)

        btn_layout = QHBoxLayout()

        self.run_btn = QPushButton("▶ Run Step")
        self.run_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: 6px; padding: 10px 24px; font-weight: bold; }}
        """)
        self.run_btn.clicked.connect(self._run_step)
        btn_layout.addWidget(self.run_btn)

        self.next_btn = QPushButton("→ Next Step")
        self.next_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_SUCCESS}; color: white; border: none;
            border-radius: 6px; padding: 10px 24px; font-weight: bold; }}
        """)
        self.next_btn.clicked.connect(self._next_step)
        btn_layout.addWidget(self.next_btn)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 10px 24px; }}
        """)
        self.back_btn.clicked.connect(self._prev_step)
        btn_layout.addWidget(self.back_btn)

        action_layout.addLayout(btn_layout)
        layout.addWidget(action_group)

        self._update_step_display()

    def _update_step_display(self):
        self.step_label.setText(f"Step {self._current_step + 1}/{len(self.STEPS)}: {self.STEPS[self._current_step]}")
        dots = []
        for i, s in enumerate(self.STEPS):
            if i < self._current_step:
                dots.append(f"● {s}")
            elif i == self._current_step:
                dots.append(f"► {s}")
            else:
                dots.append(f"○ {s}")
        self.progress_label.setText("  ".join(dots))
        self.run_btn.setEnabled(True)
        self.content.append(f"\n--- {self.STEPS[self._current_step]} Step ---")

    def _run_step(self):
        step_name = self.STEPS[self._current_step]

        try:
            if step_name == "Decision":
                action_type = self.action_input.text().strip() or "observability_read"
                result = self._gov.evaluate(action_type)
                ctx = self._router.get_context()
                ctx.set_decision(result.get("data", {}).get("action_id", ""))
                text = f"Decision: {result.get('data', {}).get('decision', 'N/A')}\n"
                text += f"Risk: {result.get('data', {}).get('risk_level', 'N/A')}\n"
                text += f"Reasoning: {result.get('data', {}).get('reasoning', 'N/A')}"
                self.content.setPlainText(text)

            elif step_name == "Approval":
                ctx = self._router.get_context()
                result = self._gov.list_workflows()
                if result:
                    wf = result[0]
                    text = f"Active Workflow: {wf.get('workflow_id', 'N/A')[:12]}\n"
                    text += f"State: {wf.get('state', 'N/A')}\n"
                    text += f"Action: {wf.get('action_type', 'N/A')}\n"
                    text += f"Signatures: {wf.get('signature_count', 0)}/{wf.get('required_signatures', 0)}"
                    ctx.set_approval(wf.get("workflow_id", ""))
                else:
                    text = "No active approval workflows."
                self.content.setPlainText(text)

            elif step_name == "Event":
                ctx = self._router.get_context()
                eid = self._truth.emit_event("inventory", "stock_movement", "wf_test_001",
                                             {"quantity": 10, "direction": "out"})
                text = f"Event Emitted: {eid}\n"
                ctx.set_event(eid, "inventory", "wf_test_001")
                event = self._truth.get_event(eid)
                if event:
                    text += f"Domain: {event.get('domain', '')}\n"
                    text += f"Type: {event.get('event_type', '')}"
                self.content.setPlainText(text)

            elif step_name == "Truth Verification":
                ctx = self._router.get_context()
                result = self._truth.verify_claim("stock_movement", ctx.selected_aggregate_id)
                d = result.get("data", {}) if isinstance(result, dict) else {}
                text = f"Claim Verified: {d.get('verified', False)}\n"
                text += f"Evidence: {d.get('evidence_event_ids', [])}\n"
                text += f"Missing: {d.get('missing_entities', [])}"
                self.content.setPlainText(text)

            elif step_name == "Observability Trace":
                ctx = self._router.get_context()
                trace = self._obs.trace_aggregate(ctx.selected_domain or "inventory",
                                                   ctx.selected_aggregate_id)
                d = trace.get("data", trace) if isinstance(trace, dict) else trace
                text = f"Trace: {d.get('trace_id', 'N/A')[:12]}\n"
                text += f"Events: {d.get('event_count', 0)}\n"
                text += f"Hash: {d.get('integrity_hash', '')[:16]}..."
                self.content.setPlainText(text)

            elif step_name == "Intelligence Insight":
                ctx = self._router.get_context()
                drift = self._intel.get_aggregate_drift(
                    ctx.selected_domain or "inventory", ctx.selected_aggregate_id
                )
                d = drift.get("data", drift) if isinstance(drift, dict) else drift
                text = f"Drift Score: {d.get('drift_score', 'N/A')}\n"
                text += f"Velocity: {d.get('drift_velocity', 'N/A')}\n"
                text += f"Confidence: {d.get('confidence_level', 'N/A')}"
                self.content.setPlainText(text)

            self.run_btn.setEnabled(False)
        except Exception as e:
            self.content.setPlainText(f"Error at {step_name}: {e}")

    def _next_step(self):
        if self._current_step < len(self.STEPS) - 1:
            self._current_step += 1
            self._update_step_display()
            self.run_btn.setEnabled(True)

    def _prev_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._update_step_display()
            self.run_btn.setEnabled(True)

    def set_api_client(self, client: APIClient):
        self._api = client
        self._gov = GovernanceAPIClient(client)
        self._truth = TruthAPIClient(client)
        self._obs = ObservabilityAPIClient(client)
