"""
Phase 5B.9 — Replay Time-Travel UI.

Visualize system state evolution over time using the deterministic
replay engine. Read-only time-travel visualization.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTextEdit, QSlider,
                                 QSpinBox, QGroupBox, QTableWidget,
                                 QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.observability_client import ObservabilityAPIClient
from ui.components.tables import build_table_stylesheet
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
    BORDER_RADIUS_SM,
    TEXT_BODY, TEXT_PAGE_TITLE,
                           MARGIN_PAGE, SPACING_6, BORDER_RADIUS_MD, BORDER_RADIUS_SM, SPACING_XS)
from ui.constants import TEXT_PAGE_TITLE, TEXT_BODY


class ReplayTimeTravelScreen(QWidget):
    """Time-travel replay visualization. Read-only."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = ObservabilityAPIClient(api_client or APIClient())
        self._current_sequence = 0
        self._max_sequence = 0
        self._build_ui()
        QTimer.singleShot(200, self._load_initial)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("Replay Time-Travel")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        self.info_label = QLabel("DETERMINISTIC REPLAY · READ-ONLY")
        self.info_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}px; font-style: italic;")
        header.addWidget(self.info_label, alignment=Qt.AlignRight)
        layout.addLayout(header)

        # Controls
        ctrl_group = QGroupBox("Replay Controls")
        ctrl_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px; padding-top: 20px; }}
        """)

        ctrl_layout = QVBoxLayout(ctrl_group)

        # Step controls
        step_layout = QHBoxLayout()
        for label, cb in [
            ("⏮ First", lambda: self._go_to(0)),
            ("◀ Step Back", self._step_back),
            ("Step Forward ▶", self._step_forward),
            ("⏭ Latest", self._go_latest),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; }}
                QPushButton:hover {{ background: {COLOR_PRIMARY}; color: white; }}
            """)
            btn.clicked.connect(cb)
            step_layout.addWidget(btn)

        ctrl_layout.addLayout(step_layout)

        # Sequence slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Sequence:"))
        self.seq_spin = QSpinBox()
        self.seq_spin.setMinimum(0)
        self.seq_spin.setMaximum(1000)
        self.seq_spin.setStyleSheet(f"""
            QSpinBox {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_XS}px; }}
        """)
        self.seq_spin.valueChanged.connect(lambda v: self._render(v))
        slider_layout.addWidget(self.seq_spin)

        self.seq_slider = QSlider(Qt.Horizontal)
        self.seq_slider.setMinimum(0)
        self.seq_slider.setMaximum(1000)
        self.seq_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 6px; background: {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_SM}px; }}
            QSlider::handle:horizontal {{ background: {COLOR_PRIMARY}; width: 14px;
            border-radius: {BORDER_RADIUS_MD}px; margin: -4px 0; }}
        """)
        self.seq_slider.valueChanged.connect(lambda v: self.seq_spin.setValue(v))
        slider_layout.addWidget(self.seq_slider)

        self.position_label = QLabel("Position: 0 / 0")
        self.position_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}px;")
        slider_layout.addWidget(self.position_label)

        ctrl_layout.addLayout(slider_layout)
        layout.addWidget(ctrl_group)

        # Event table at current position
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Event ID", "Type", "Domain", "Summary"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(build_table_stylesheet())
        layout.addWidget(self.table)

        # Integrity hash
        self.hash_label = QLabel("")
        self.hash_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}px;")
        layout.addWidget(self.hash_label)

    def _load_initial(self):
        try:
            resp = self._api.get_replay_state(0)
            data = resp.get("data", resp) if isinstance(resp, dict) else {}
            self._max_sequence = data.get("total_events_in_range", data.get("to_sequence", 0))
            self.seq_spin.setMaximum(max(self._max_sequence, 1))
            self.seq_slider.setMaximum(max(self._max_sequence, 1))
            self._render(0)
        except Exception:
            pass

    def _render(self, sequence: int):
        self._current_sequence = sequence
        self.position_label.setText(f"Position: {sequence} / {self._max_sequence}")
        try:
            resp = self._api.render_at_sequence(sequence)
            data = resp.get("data", resp) if isinstance(resp, dict) else {}
            events = data.get("events", data) if isinstance(data, list) else data.get("events", [])

            self.table.setRowCount(len(events))
            for i, evt in enumerate(events):
                self.table.setItem(i, 0, QTableWidgetItem(str(evt.get("event_id", ""))[:12]))
                self.table.setItem(i, 1, QTableWidgetItem(evt.get("event_type", "")))
                self.table.setItem(i, 2, QTableWidgetItem(evt.get("domain", "")))
                self.table.setItem(i, 3, QTableWidgetItem(str(evt.get("summary", ""))[:60]))

            try:
                hash_resp = self._api.get_replay_hash(0, sequence)
                hdata = hash_resp.get("data", hash_resp) if isinstance(hash_resp, dict) else {}
                self.hash_label.setText(f"Replay Hash: {hdata.get('hash', 'N/A')[:32]}...")
            except Exception:
                self.hash_label.setText("")

        except Exception as e:
            self.table.setRowCount(0)

    def _step_forward(self):
        if self._current_sequence < self._max_sequence:
            self.seq_spin.setValue(self._current_sequence + 1)

    def _step_back(self):
        if self._current_sequence > 0:
            self.seq_spin.setValue(self._current_sequence - 1)

    def _go_to(self, sequence: int):
        self.seq_spin.setValue(sequence)

    def _go_latest(self):
        self.seq_spin.setValue(self._max_sequence)

    def set_api_client(self, client: APIClient):
        self._api = ObservabilityAPIClient(client)
