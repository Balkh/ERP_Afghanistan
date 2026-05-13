"""
Phase 5B.9 — Decision Options Screen.

Displays AI-generated structured decision alternatives.
READ-ONLY — no execution buttons, no state mutation.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QScrollArea, QGridLayout,
                                 QGroupBox, QTextEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE)


class _OptionCard(QFrame):
    def __init__(self, title: str, description: str, options: list,
                 recommended_id: str, context: str):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background: {COLOR_BG_ELEVATED}; border: 1px solid {COLOR_BORDER};
            border-radius: 8px; padding: 12px; margin: 4px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_SM)

        d_type = QLabel(title)
        d_type.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 16px; font-weight: bold;")
        layout.addWidget(d_type)

        ctx = QLabel(context[:120])
        ctx.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(ctx)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COLOR_BORDER};")
        layout.addWidget(sep)

        for opt in options:
            opt_frame = QFrame()
            opt_frame.setStyleSheet(f"""
                QFrame {{ background: {COLOR_BG_SURFACE}; border: 1px solid {COLOR_BORDER};
                border-radius: 6px; padding: 8px; margin: 2px; }}
            """)
            ol = QVBoxLayout(opt_frame)

            o_title = QLabel(opt.get("action_summary", "Option"))
            o_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 12px; font-weight: bold;")
            ol.addWidget(o_title)

            meta = QLabel(f"Risk: {opt.get('risk_level', 'N/A')}  |  Confidence: {opt.get('confidence', 0):.0%}")
            meta.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
            ol.addWidget(meta)

            if opt.get("option_id") == recommended_id:
                rec = QLabel("★ RECOMMENDED")
                rec.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 10px; font-weight: bold;")
                ol.addWidget(rec)

            layout.addWidget(opt_frame)

        layout.addStretch()


class DecisionOptionsScreen(QWidget):
    """Read-only decision options viewer."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = AutonomousAPIClient(api_client or APIClient())
        self._build_ui()
        QTimer.singleShot(200, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Decision Options & Alternatives")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        info = QLabel("READ-ONLY · No execution capability")
        info.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-style: italic;")
        header.addWidget(info)

        self.refresh_btn = QPushButton("⟳ Refresh")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        """)
        self.refresh_btn.clicked.connect(self._refresh)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {COLOR_BG_MAIN}; border: none;")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(SPACING_MD)

        self.empty_label = QLabel("Loading decision options...")
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 14px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.container_layout.addWidget(self.empty_label)

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def _refresh(self):
        try:
            resp = self._api.get_decision_options()
            data = resp.get("data", {}) if isinstance(resp, dict) else {}
            decisions = data.get("decisions", [])

            self._clear_container()

            if not decisions:
                self.empty_label = QLabel("No decision options available.")
                self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 14px;")
                self.empty_label.setAlignment(Qt.AlignCenter)
                self.container_layout.addWidget(self.empty_label)
                return

            for d in decisions:
                card = _OptionCard(
                    title=d.get("decision_type", "Decision").replace("_", " ").title(),
                    description=d.get("context_summary", ""),
                    options=d.get("options", []),
                    recommended_id=d.get("recommended_option_id", ""),
                    context=d.get("context_summary", ""),
                )
                self.container_layout.addWidget(card)

        except Exception as e:
            self._clear_container()
            err = QLabel(f"Error loading decisions: {e}")
            err.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 12px;")
            self.container_layout.addWidget(err)

    def _clear_container(self):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_api_client(self, client: APIClient):
        self._api = AutonomousAPIClient(client)
