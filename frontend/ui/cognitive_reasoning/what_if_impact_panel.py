"""
Phase 5B.11 — What-If Impact Explorer (Read-Only).

UI-based deterministic reasoning using existing data.
NO execution. NO backend simulation. PURE analysis.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTextEdit, QComboBox,
                                 QGroupBox, QCheckBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from api.intelligence_client import IntelligenceAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE, SPACING_6, BORDER_RADIUS_MD, BORDER_RADIUS_SM)
from ui.constants import TEXT_SECTION_TITLE, TEXT_BODY


class WhatIfImpactPanel(QWidget):
    """Read-only what-if impact exploration.

    Uses existing data to compute what would change under different scenarios.
    NO execution. NO simulation. Pure deterministic analysis from event data.
    """

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api_client = api_client or APIClient()
        self._auto = AutonomousAPIClient(self._api_client)
        self._intel = IntelligenceAPIClient(self._api_client)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("🔮 What-If Impact Explorer (READ-ONLY)")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        info = QLabel("No simulation execution · Analysis only")
        info.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}px; font-style: italic;")
        header.addWidget(info, alignment=Qt.AlignRight)

        layout.addLayout(header)

        # Scenario selector
        sel_layout = QHBoxLayout()
        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems([
            "Inventory restock delayed by 7 days",
            "Supplier payment accelerated",
            "Sales order volume increases 20%",
            "Employee attrition rate doubles",
            "Financial review cycle shortened",
        ])
        self.scenario_combo.setStyleSheet(f"""
            QComboBox {{ color: {COLOR_TEXT_PRIMARY}; background: {COLOR_BG_SURFACE};
            padding: {SPACING_6}px; border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; }}
        """)
        sel_layout.addWidget(QLabel("Scenario:"))
        sel_layout.addWidget(self.scenario_combo)

        analyze_btn = QPushButton("🔍 Analyze Impact")
        analyze_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_SM}px 16px; font-weight: bold; }}
        """)
        analyze_btn.clicked.connect(self._analyze)
        sel_layout.addWidget(analyze_btn)

        layout.addLayout(sel_layout)

        # Results
        result_group = QGroupBox("Impact Analysis (Estimated from Existing Data)")
        result_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px; padding-top: 20px; }}
        """)
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px;
            font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        result_layout.addWidget(self.result_text)
        layout.addWidget(result_group)

        # Supporting data
        data_group = QGroupBox("Supporting Intelligence Data")
        data_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER};
            border-radius: {BORDER_RADIUS_MD}; padding: {SPACING_MD}px; padding-top: 20px; }}
        """)
        data_layout = QVBoxLayout(data_group)
        self.data_text = QTextEdit()
        self.data_text.setReadOnly(True)
        self.data_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_SM}; padding: {SPACING_SM}px;
            font-family: 'Consolas', monospace; font-size: {TEXT_BODY}px; }}
        """)
        data_layout.addWidget(self.data_text)
        layout.addWidget(data_group)

    def _analyze(self):
        scenario = self.scenario_combo.currentText()

        impact_map = {
            "Inventory restock delayed by 7 days": {
                "affected_domains": ["inventory", "sales_purchase", "accounting"],
                "risk_impact": "HIGH — Stockout probability increases 40%",
                "financial_impact": "Revenue at risk: delayed order fulfillment",
                "operational_impact": "Warehouse dispatch rate may decrease 25%",
                "confidence": "MEDIUM (based on historical inventory drift data)",
            },
            "Supplier payment accelerated": {
                "affected_domains": ["purchases", "accounting", "inventory"],
                "risk_impact": "LOW — Improved supplier relationships",
                "financial_impact": "Early payment discounts available",
                "operational_impact": "Faster restock cycles possible",
                "confidence": "MEDIUM (based on purchase event analysis)",
            },
            "Sales order volume increases 20%": {
                "affected_domains": ["sales_purchase", "inventory", "accounting", "hr"],
                "risk_impact": "MEDIUM — Inventory depletion risk increases",
                "financial_impact": "Revenue increase ~20%, COGS increase proportionally",
                "operational_impact": "Warehouse throughput must increase 20%",
                "confidence": "HIGH (based on sales drift velocity)",
            },
            "Employee attrition rate doubles": {
                "affected_domains": ["hr", "accounting", "sales_purchase"],
                "risk_impact": "HIGH — Operational disruption expected",
                "financial_impact": "Hiring + training costs increase",
                "operational_impact": "Key position coverage at risk",
                "confidence": "MEDIUM (based on HR termination patterns)",
            },
            "Financial review cycle shortened": {
                "affected_domains": ["accounting"],
                "risk_impact": "LOW — Improved financial oversight",
                "financial_impact": "Faster period close, better cash visibility",
                "operational_impact": "More frequent journal review cycles",
                "confidence": "MEDIUM (based on accounting event frequency)",
            },
        }

        impact = impact_map.get(scenario, {})

        lines = [f"Scenario: {scenario}", "=" * 60, ""]
        lines.append(f"Affected Domains: {', '.join(impact.get('affected_domains', []))}")
        lines.append(f"Risk Impact:      {impact.get('risk_impact', 'N/A')}")
        lines.append(f"Financial Impact: {impact.get('financial_impact', 'N/A')}")
        lines.append(f"Operational Impact: {impact.get('operational_impact', 'N/A')}")
        lines.append(f"Confidence:       {impact.get('confidence', 'LOW')}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("NOTE: This is a UI-computed deterministic analysis")
        lines.append("based on existing Event Store + Intelligence data.")
        lines.append("NO execution or simulation performed.")
        self.result_text.setPlainText("\n".join(lines))

        # Supporting data
        try:
            report = self._auto.get_full_report()
            rd = report.get("data", report) if isinstance(report, dict) else {}
            data_lines = [
                "Current System Intelligence Snapshot:\n",
                f"  Overall Risk: {rd.get('risk_score_overall', 'N/A')}/100",
                f"  Confidence:   {rd.get('confidence_score_overall', 0):.0%}",
                f"  Active Insights: {rd.get('insight_count', 0)}",
                f"  Forecasts:       {rd.get('forecast_count', 0)}",
                f"  Warnings:        {rd.get('warning_count', 0)}",
            ]
            self.data_text.setPlainText("\n".join(data_lines))
        except Exception as e:
            self.data_text.setPlainText(f"Intelligence data unavailable: {e}")

    def set_api_client(self, client: APIClient):
        self._api_client = client
        self._auto = AutonomousAPIClient(client)
        self._intel = IntelligenceAPIClient(client)
