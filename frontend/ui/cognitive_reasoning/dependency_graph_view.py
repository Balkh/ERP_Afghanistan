"""
Phase 5B.11 — Cross-Domain Dependency Graph View.

Interactive dependency visualization showing:
- Domain ↔ Domain relationships
- Observability signals linked to domains
- Intelligence anomalies mapped to root domains

UI-computed only. No backend graph computation.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QFrame, QTextEdit, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from api.client import APIClient
from api.observability_client import ObservabilityAPIClient
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           COLOR_INFO, COLOR_BORDER, SPACING_LG, SPACING_MD, SPACING_SM,
                           MARGIN_PAGE)

# Known cross-domain dependency matrix (UI-level, computed from Phase 5B.4 correlation patterns)
DOMAIN_DEPENDENCIES = [
    ("inventory", "sales_purchase", "Inventory supplies sales orders", COLOR_INFO),
    ("sales_purchase", "inventory", "Sales trigger stock movements", COLOR_WARNING),
    ("inventory", "accounting", "Stock movements create journal entries", COLOR_INFO),
    ("sales_purchase", "accounting", "Payments and orders create journal entries", COLOR_INFO),
    ("hr", "accounting", "Payroll creates journal entries", COLOR_INFO),
    ("fixed_assets", "accounting", "Asset depreciation creates journal entries", COLOR_WARNING),
    ("inventory", "hr", "Inventory levels affect HR workload", COLOR_TEXT_MUTED),
    ("sales_purchase", "inventory", "Order approvals involve employees", COLOR_TEXT_MUTED),
]


class DependencyGraphView(QWidget):
    """Interactive cross-domain dependency visualization."""

    def __init__(self, api_client: APIClient = None):
        super().__init__()
        self._api = ObservabilityAPIClient(api_client or APIClient())
        self._build_ui()
        QTimer.singleShot(300, self._refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        header = QHBoxLayout()
        title = QLabel("🔗 Cross-Domain Dependency Map")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header.addWidget(title)

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {COLOR_PRIMARY}; color: white; border: none;
            border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        """)
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn, alignment=Qt.AlignRight)

        layout.addLayout(header)

        info = QLabel("Lines represent inferred causal relationships between enterprise domains. "
                       "Thicker line = stronger correlation.")
        info.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-style: italic;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Dependency links (text-based graph visualization)
        self.graph_text = QTextEdit()
        self.graph_text.setReadOnly(True)
        self.graph_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 12px;
            font-family: 'Consolas', monospace; font-size: 12px; }}
        """)
        layout.addWidget(self.graph_text)

        # Correlation data from observability
        corr_group = QGroupBox("Observability Correlation Data")
        corr_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER};
            border-radius: 6px; padding: 12px; padding-top: 20px; }}
        """)
        corr_layout = QVBoxLayout(corr_group)
        self.corr_text = QTextEdit()
        self.corr_text.setReadOnly(True)
        self.corr_text.setStyleSheet(f"""
            QTextEdit {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 8px;
            font-family: 'Consolas', monospace; font-size: 11px; }}
        """)
        corr_layout.addWidget(self.corr_text)
        layout.addWidget(corr_group)

    def _refresh(self):
        # Render dependency graph (text-based)
        lines = []
        lines.append("=" * 60)
        lines.append("ENTERPRISE DEPENDENCY MAP")
        lines.append("=" * 60)
        lines.append("")

        deps_by_source: dict = {}
        for src, tgt, desc, _ in DOMAIN_DEPENDENCIES:
            if src not in deps_by_source:
                deps_by_source[src] = []
            deps_by_source[src].append((tgt, desc))

        for src in sorted(deps_by_source.keys()):
            lines.append(f"  [{src.upper()}]")
            for tgt, desc in deps_by_source[src]:
                lines.append(f"    │  →  [{tgt.upper()}]  ({desc})")
            lines.append("")

        lines.append("-" * 60)
        lines.append("LEGEND:")
        lines.append("  [DOMAIN]  = Enterprise functional domain")
        lines.append("  →  = Dependency / data flow direction")
        lines.append("  (...)  = Description of relationship")
        lines.append("=" * 60)

        self.graph_text.setPlainText("\n".join(lines))

        # Fetch observability correlation data
        try:
            deps = self._api.get_domain_dependencies()
            d = deps.get("data", deps) if isinstance(deps, dict) else {}
            corr_lines = ["Observability Domain Dependencies:\n"]
            for domain, related in d.items():
                corr_lines.append(f"  {domain}: {', '.join(related)}")
            self.corr_text.setPlainText("\n".join(corr_lines))
        except Exception as e:
            self.corr_text.setPlainText(f"Correlation data unavailable: {e}")

    def set_api_client(self, client: APIClient):
        self._api = ObservabilityAPIClient(client)
