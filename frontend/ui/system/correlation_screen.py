from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO, COLOR_TABLE_BORDER_LIGHT, COLOR_TABLE_HEADER_BG_LIGHT)
"""
System Correlation Screen - Unified Decision Ecosystem.
Visualizes end-to-end business event chains and ERP-wide consistency.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QScrollArea, QListWidget, 
                               QListWidgetItem, QTableWidget, QTableWidgetItem,
                               QHeaderView, QSizePolicy, QGroupBox, QPushButton)
from PySide6.QtCore import Qt, QPointF, QTimer, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient

from ui.screens.base_screen import BaseScreen
from ui.constants import (COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO)
from api.correlation_service import CorrelationIntelligenceService


class EcosystemGraphWidget(QWidget):
    """Visualizes the correlation between different ERP modules for a specific chain."""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(250)
        self.nodes = [] # List of {id, label, type, status, x, y}
        self.links = [] # List of (from_id, to_id)
        self.colors = {
            "Invoice": COLOR_PRIMARY,
            "Workflow": "#f9e2af",
            "Accounting": "#cba6f7",
            "Finance": COLOR_STATUS_VALID,
            "Inventory": COLOR_STATUS_WARNING
        }

    def set_chain(self, chain):
        """Set up nodes and links from a correlation chain."""
        if not chain:
            self.nodes = []
            self.links = []
            self.update()
            return
            
        self.nodes = []
        raw_nodes = chain.get('nodes', [])
        
        # Calculate horizontal positions
        w = self.width() if self.width() > 100 else 600
        step = (w - 100) / (max(len(raw_nodes) - 1, 1))
        
        for i, n in enumerate(raw_nodes):
            self.nodes.append({
                **n,
                "x": 50 + i * step,
                "y": 100
            })
            
        self.links = chain.get('links', [])
        self.update()

    def paintEvent(self, event):
        if not self.nodes:
            painter = QPainter(self)
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignCenter, "Select an event chain to visualize correlation")
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Links (Edges)
        painter.setPen(QPen(QColor(COLOR_TABLE_BORDER_LIGHT), 2, Qt.DashLine))
        node_map = {n['id']: n for n in self.nodes}
        for start_id, end_id in self.links:
            if start_id in node_map and end_id in node_map:
                n1, n2 = node_map[start_id], node_map[end_id]
                painter.drawLine(n1['x'] + 40, n1['y'] + 20, n2['x'], n2['y'] + 20)
                
        # Draw Nodes
        for n in self.nodes:
            x, y = n['x'], n['y']
            color = QColor(self.colors.get(n['type'], COLOR_TEXT_PRIMARY))
            
            # Node Box
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(QColor(COLOR_BG_MAIN)))
            painter.drawRoundedRect(x, y, 90, 45, 8, 8)
            
            # Status Indicator Dot
            status_color = COLOR_SUCCESS if n['status'] not in ['NONE', 'PENDING', 'MISSING'] else COLOR_WARNING
            if n['status'] == 'MISSING': status_color = COLOR_DANGER
            painter.setBrush(QBrush(QColor(status_color)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(x + 10, y + 10), 4, 4)
            
            # Text
            painter.setPen(QColor(COLOR_TEXT_SECONDARY))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(x + 20, y + 15, n['type'])

            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(x + 10, y + 35, n['label'])


class SystemCorrelationScreen(BaseScreen):
    """Unified System Correlation Dashboard."""
    
    def __init__(self, parent=None, screen_id="system_correlation", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._service = CorrelationIntelligenceService(api_client)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM)
        layout.setSpacing(SPACING_LG + SPACING_XS)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Cross-System Correlation")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        
        self.consistency_card = QFrame()
        self.consistency_card.setFixedWidth(220)
        self.consistency_card.setStyleSheet(f"background: {COLOR_TABLE_HEADER_BG_LIGHT}; border-radius: 15px; border: 1px solid {COLOR_PRIMARY};")
        cc_layout = QHBoxLayout(self.consistency_card)
        self.score_label = QLabel("ERP CONSISTENCY: 100%")
        self.score_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; font-size: 11px;")
        cc_layout.addStretch()
        cc_layout.addWidget(self.score_label)
        cc_layout.addStretch()
        
        self.refresh_btn = QPushButton("Re-Correlate")
        self.refresh_btn.clicked.connect(self._load_correlation)
        
        header.addWidget(title)
        header.addWidget(self.consistency_card)
        header.addStretch()
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)
        
        # Main Grid
        grid = QGridLayout()
        grid.setSpacing(SPACING_LG + SPACING_XS)
        
        # 1. Business Event Chains (Left)
        chains_group = self._create_group("Active Business Event Chains", 400)
        self.chains_table = QTableWidget()
        self.chains_table.setColumnCount(4)
        self.chains_table.setHorizontalHeaderLabels(["ID", "Type", "Health", "Status"])
        self.chains_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.chains_table.verticalHeader().setVisible(False)
        self.chains_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.chains_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.chains_table.cellClicked.connect(self._on_chain_selected)
        self.chains_table.setStyleSheet(f"QTableWidget {{ background: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY}; border: none; }} QHeaderView::section {{ background: {COLOR_TABLE_HEADER_BG_LIGHT}; color: {COLOR_PRIMARY}; border: none; padding: 6px; font-weight: bold; }}")
        chains_group.layout().addWidget(self.chains_table)
        grid.addWidget(chains_group, 0, 0)
        
        # 2. Correlation Graph (Right)
        graph_group = self._create_group("Decision Ecosystem Graph", 400)
        self.graph = EcosystemGraphWidget()
        graph_group.layout().addWidget(self.graph)
        grid.addWidget(graph_group, 0, 1)
        
        # 3. Impact Analysis (Bottom)
        impact_group = self._create_group("Impact Propagation & Root Cause Analysis", 250)
        self.impact_list = QListWidget()
        self.impact_list.setStyleSheet(f"background: {COLOR_BG_SURFACE}; border: none; border-radius: 8px;")
        impact_group.layout().addWidget(self.impact_list)
        grid.addWidget(impact_group, 1, 0, 1, 2)
        
        layout.addLayout(grid)

    def _create_group(self, title, min_h):
        group = QGroupBox(title)
        group.setMinimumHeight(min_h)
        group.setStyleSheet(f"QGroupBox {{ color: {COLOR_PRIMARY}; font-weight: bold; border: 1px solid {COLOR_TABLE_HEADER_BG_LIGHT}; border-radius: 12px; margin-top: 15px; background: {COLOR_BG_MAIN}; }} QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}")
        QVBoxLayout(group)
        group.layout().setContentsMargins(SPACING_MD,  SPACING_XL + SPACING_SM,  SPACING_MD,  SPACING_MD)
        return group

    def _on_screen_shown(self):
        self._load_correlation()

    def _load_correlation(self):
        self.refresh_btn.setEnabled(False)
        self.score_label.setText("CORRELATING...")
        
        # Using a timer to simulate async if needed, but for now direct call
        # Since service uses api_client (which might be async in some apps, 
        # but here we follow existing QThread patterns if volume is high)
        res = self._service.build_correlation_ecosystem()
        if res.get('status') == 'ok':
            self._update_ui(res)
        self.refresh_btn.setEnabled(True)

    def _update_ui(self, data):
        self.score_label.setText(f"ERP CONSISTENCY: {data['consistency_score']}%")
        
        chains = data.get('chains', [])
        self.chains_table.setRowCount(len(chains))
        for i, c in enumerate(chains):
            self.chains_table.setItem(i, 0, QTableWidgetItem(c['id']))
            self.chains_table.setItem(i, 1, QTableWidgetItem(c['entity']))
            
            health_item = QTableWidgetItem(f"{c['health_score']}%")
            health_color = COLOR_SUCCESS if c['health_score'] > 80 else (COLOR_WARNING if c['health_score'] > 50 else COLOR_DANGER)
            health_item.setForeground(QColor(health_color))
            self.chains_table.setItem(i, 2, health_item)
            
            self.chains_table.setItem(i, 3, QTableWidgetItem(c['status']))

    def _on_chain_selected(self, row, col):
        chain_id = self.chains_table.item(row, 0).text()
        chain = next((c for c in self._service.event_chains if c['id'] == chain_id), None)
        
        # Update Graph
        self.graph.set_chain(chain)
        
        # Update Impact Analysis
        self.impact_list.clear()
        analysis = self._service.analyze_impact(chain_id)
        impacts = analysis.get('impacts', [])
        
        if not impacts:
            item = QListWidgetItem("✅ No downstream risks detected. Chain is healthy.")
            item.setForeground(QColor(COLOR_SUCCESS))
            self.impact_list.addItem(item)
        else:
            for imp in impacts:
                item = QListWidgetItem(f"🚨 {imp['severity']}: {imp['description']}")
                item.setForeground(QColor(COLOR_DANGER if imp['severity'] == 'HIGH' else COLOR_WARNING))
                self.impact_list.addItem(item)
                
            # Add Root Cause hint
            root_cause = chain['steps'][0]['name'] if chain['steps'] else "Unknown"
            rc_item = QListWidgetItem(f"🔍 Root Cause Indicator: Inconsistency started at {root_cause}")
            rc_item.setForeground(QColor(COLOR_INFO))
            self.impact_list.addItem(rc_item)
