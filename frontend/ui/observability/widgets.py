from PySide6.QtWidgets import (QFrame, QLabel, QProgressBar, QWidget,
                                QVBoxLayout, QHBoxLayout, QScrollArea)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QFont, QPainter, QColor
from typing import List, Dict, Any

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, COLOR_SUCCESS, COLOR_DANGER, COLOR_INFO,
                          COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_BG_MAIN, COLOR_BG_SURFACE,
                          COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_BORDER_LIGHT,
                          SPACING_NONE, TEXT_BODY, TEXT_LABEL, TEXT_TABLE,
                          BORDER_RADIUS_MD, BORDER_RADIUS_PILL,
    BORDER_RADIUS_SM)
from ui.constants import COLOR_STATUS_VALID, COLOR_STATUS_WARNING


class StatusIndicator(QFrame):
    def __init__(self, label_text="Status", initial_status="unknown", parent=None):
        super().__init__(parent)
        self.setObjectName("statusIndicator")
        self.setFixedSize(120, 28)
        self.setStyleSheet("background-color: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        layout.addWidget(self.dot, 0, Qt.AlignVCenter)

        self.label = QLabel(label_text)
        self.label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(self.label, 0, Qt.AlignVCenter)

        layout.addStretch()
        self.set_status(initial_status)

    def set_status(self, status: str):
        s = status.lower()
        if s in ("healthy", "operational", "optimal", "up", "stable", "ok", "connected"):
            color = COLOR_STATUS_VALID
            text = "Operational"
        elif s in ("degraded", "warning", "slow", "pending", "partial"):
            color = COLOR_STATUS_WARNING
            text = "Degraded"
        elif s in ("down", "critical", "error", "failed", "unreachable", "disconnected"):
            color = COLOR_DANGER
            text = "Critical"
        else:
            color = COLOR_TEXT_MUTED
            text = "Unknown"

        self.dot.setStyleSheet(
            f"background-color: {color}; border-radius: {BORDER_RADIUS_SM}px; min-width: 10px; min-height: 10px;"
        )
        self.label.setText(text)


class SeverityBadge(QLabel):
    SEVERITY_COLORS = {
        "info": (COLOR_INFO, COLOR_BG_SURFACE),
        "low": (COLOR_INFO, COLOR_BG_SURFACE),
        "medium": (COLOR_STATUS_WARNING, COLOR_BG_SURFACE),
        "high": (COLOR_STATUS_WARNING, COLOR_BG_SURFACE),
        "critical": (COLOR_DANGER, COLOR_BG_SURFACE),
    }

    def __init__(self, severity="info", text=None, parent=None):
        super().__init__(parent)
        self._severity = severity.lower()
        display = (text or severity).upper()
        self.setText(display)
        self._apply_style()

    def set_severity(self, severity: str):
        self._severity = severity.lower()
        self._apply_style()

    def _apply_style(self):
        bg, fg = self.SEVERITY_COLORS.get(
            self._severity, (COLOR_TEXT_MUTED, COLOR_BG_MAIN)
        )
        self.setStyleSheet(
            f"""
            background-color: {bg};
            color: {COLOR_BG_MAIN};
            padding: {SPACING_XS}px {SPACING_SM}px;
            border-radius: {BORDER_RADIUS_SM};
            font-size: {TEXT_TABLE}px;
            font-weight: bold;
            """
        )
        self.setFont(QFont("Segoe UI", TEXT_TABLE, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignCenter)


class TrendArrow(QLabel):
    def __init__(self, direction="up", color=None, parent=None):
        super().__init__(parent)
        self._direction = direction
        arrow = "▲" if direction == "up" else "▼"
        c = color or (COLOR_SUCCESS if direction == "up" else COLOR_DANGER)
        self.setText(arrow)
        self.setStyleSheet(f"color: {c}; font-size: {TEXT_BODY}px; font-weight: bold; border: none;")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(20)


class HealthBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(100)
        self.setTextVisible(True)
        self.setFixedHeight(22)
        self.setMinimumWidth(200)
        self.setFormat("%p%")
        self.setAlignment(Qt.AlignCenter)
        self._update_style()

    def set_value(self, value: int):
        clamped = max(0, min(100, int(value)))
        self.setValue(clamped)
        self._update_style()

    def _update_style(self):
        v = self.value()
        if v >= 80:
            color = COLOR_STATUS_VALID
        elif v >= 50:
            _color = COLOR_STATUS_WARNING
        else:
            __color = COLOR_DANGER

        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_PILL}px;
                text-align: center;
                font-size: {TEXT_TABLE}px;
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
                padding: {SPACING_NONE}px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: {BORDER_RADIUS_PILL - 1}px;
            }}
        """)


class MetricCard(QFrame):
    def __init__(self, title="", value="", description="", color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {COLOR_BG_SURFACE};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: {BORDER_RADIUS_MD}px;
                border-top: 3px solid {color or COLOR_INFO};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_XS)

        self._title_label = QLabel(title)
        self._title_label.setFont(QFont("Segoe UI", TEXT_TABLE, QFont.Weight.Bold))
        self._title_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
        layout.addWidget(self._title_label)

        self._value_label = QLabel(str(value))
        self._value_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self._value_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")
        layout.addWidget(self._value_label)

        self._desc_label = QLabel(description)
        self._desc_label.setFont(QFont("Segoe UI", TEXT_TABLE))
        self._desc_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none;")
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)

    def update_value(self, value, subtitle=None, color=None):
        self._value_label.setText(str(value))
        if subtitle:
            self._desc_label.setText(subtitle)
        if color:
            self.setStyleSheet(f"""
                QFrame#metricCard {{
                    background-color: {COLOR_BG_SURFACE};
                    border: 1px solid {COLOR_BORDER_LIGHT};
                    border-radius: {BORDER_RADIUS_MD}px;
                    border-top: 3px solid {color};
                }}
            """)


class TimelineEventWidget(QFrame):
    def __init__(self, timestamp="", severity="info", description="", parent=None):
        super().__init__(parent)
        self.setObjectName("timelineEvent")
        self.setStyleSheet(f"""
            QFrame#timelineEvent {{
                background-color: {COLOR_BG_SURFACE};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: {BORDER_RADIUS_MD}px;
                margin: {SPACING_NONE}px 0px;
            }}
            QFrame#timelineEvent:hover {{
                border: 1px solid {COLOR_INFO};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_SM)

        self.badge = SeverityBadge(severity, timestamp)
        self.badge.setFixedWidth(80)
        layout.addWidget(self.badge)

        self.desc_label = QLabel(description)
        self.desc_label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.desc_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label, 1)

    def set_data(self, timestamp, severity, description):
        self.badge.set_severity(severity)
        self.desc_label.setText(description)


class IncidentCard(QFrame):
    def __init__(self, incident_id="", severity="info", status="open",
                 description="", escalation=0, parent=None):
        super().__init__(parent)
        self.setObjectName("incidentCard")
        self._severity = severity
        __severity_color = SeverityBadge.SEVERITY_COLORS.get(
            severity.lower(), (COLOR_TEXT_MUTED, COLOR_BG_MAIN)
        )[0]
        self.setStyleSheet(f"""
            QFrame#incidentCard {{
                background-color: {COLOR_BG_SURFACE};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: {BORDER_RADIUS_MD}px;
                border-left: 4px solid {severity_color};
            }}
            QFrame#incidentCard:hover {{
                border: 1px solid {COLOR_INFO};
                border-left: 4px solid {severity_color};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_XS)

        header = QHBoxLayout()
        id_label = QLabel(f"#{incident_id}")
        id_label.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        id_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")
        header.addWidget(id_label)
        header.addStretch()
        badge = SeverityBadge(severity)
        header.addWidget(badge)
        layout.addLayout(header)

        self.desc_label = QLabel(description)
        self.desc_label.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.desc_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        footer = QHBoxLayout()
        status_label = QLabel(f"Status: {status}")
        status_label.setFont(QFont("Segoe UI", TEXT_TABLE))
        status_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none;")
        footer.addWidget(status_label)
        footer.addStretch()
        esc_label = QLabel(f"Escalation: L{escalation}")
        esc_label.setFont(QFont("Segoe UI", TEXT_TABLE))
        esc_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none;")
        footer.addWidget(esc_label)
        layout.addLayout(footer)


class SectionHeader(QFrame):
    action_clicked = Signal()

    def __init__(self, title="Section", action_text=None, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionHeader")
        self.setStyleSheet("""
            QFrame#sectionHeader {{
                background-color: transparent;
                border: none;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", TEXT_BODY, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        if action_text:
            self.action_btn = QLabel(action_text)
            self.action_btn.setFont(QFont("Segoe UI", TEXT_TABLE))
            self.action_btn.setStyleSheet(f"""
                color: {COLOR_INFO};
                border: none;
            padding: {SPACING_XS}px {SPACING_SM}px;
            """)
            self.action_btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(self.action_btn)


class VirtualTimelineWidget(QScrollArea):
    MAX_VISIBLE = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("background-color: transparent;")

        self._container = QWidget()
        self._container.setStyleSheet("background-color: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(SPACING_XS)
        self._layout.addStretch()
        self.setWidget(self._container)

        self._events: List[Dict[str, Any]] = []
        self._rendered_count = 0

    def set_events(self, events: List[Dict[str, Any]]):
        self._events = events[:self.MAX_VISIBLE]
        self._render()

    def append_event(self, event: Dict[str, Any]):
        self._events.append(event)
        if len(self._events) > self.MAX_VISIBLE:
            self._events.pop(0)
        self._render()

    def clear_events(self):
        self._events.clear()
        self._render()

    def _render(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        visible = self._events[:self.MAX_VISIBLE]
        self._rendered_count = len(visible)
        for ev in visible:
            widget = TimelineEventWidget(
                timestamp=ev.get("timestamp", ""),
                severity=ev.get("severity", "info"),
                description=ev.get("description", ev.get("message", "")),
            )
            self._layout.insertWidget(self._layout.count() - 1, widget)
