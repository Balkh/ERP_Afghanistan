"""
Workflow Intelligence Screen - Live Decision Tracking System.
Provides visual analytics and real-time tracking for ERP workflows.
"""

from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QListWidget, QListWidgetItem, QGroupBox)
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont

from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, MARGIN_VERTICAL_SM, TEXT_PAGE_TITLE,
                           TEXT_SECTION_TITLE, TEXT_BODY, TEXT_TABLE, TEXT_TABLE_HEADER, BORDER_RADIUS_SM, BORDER_RADIUS_LG, BORDER_RADIUS_XL, COLOR_BG_MAIN, COLOR_BG_SURFACE,
                           COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TABLE_BORDER_LIGHT,
                           COLOR_TABLE_HEADER_BG_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY,
                           COLOR_PRIMARY_MUTED, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID)
from api.client import APIClient
from runtime.timer_registry import register_timer
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn


class WorkflowPipelineWidget(QWidget):
    """Horizontal pipeline showing workflow stages and volume."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(120)
        self.stages = [
            {'id': 'DRAFT', 'label': 'Draft', 'color': COLOR_TEXT_MUTED},
            {'id': 'PENDING_APPROVAL', 'label': 'Pending', 'color': COLOR_WARNING},
            {'id': 'APPROVED', 'label': 'Approved', 'color': COLOR_STATUS_VALID},
            {'id': 'REJECTED', 'label': 'Rejected', 'color': COLOR_DANGER},
            {'id': 'POSTED', 'label': 'Posted', 'color': COLOR_PRIMARY}
        ]
        self.data = {s['id']: 0 for s in self.stages}

    def set_data(self, counts):
        self.data.update(counts)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        __h = self.height()
        margin = 20
        step_w = (w - 2 * margin) / len(self.stages)
        
        for i, stage in enumerate(self.stages):
            x = margin + i * step_w
            y = 40
            node_r = 12
            
            # Draw line to next node
            if i < len(self.stages) - 1:
                painter.setPen(QPen(QColor(COLOR_BG_ELEVATED), 4))
                painter.drawLine(x + node_r, y + node_r, x + step_w - node_r, y + node_r)
            
            # Draw node
            count = self.data.get(stage['id'], 0)
            color = QColor(stage['color'])
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x + node_r, y + node_r), node_r, node_r)
            
            # Labels
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont("Segoe UI", TEXT_TABLE, QFont.Weight.Bold))
            painter.drawText(int(x), y + 45, int(step_w), 20, Qt.AlignCenter, stage['label'])

            painter.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
            painter.drawText(int(x), y - 25, int(step_w), 30, Qt.AlignCenter, str(count))


class WorkflowRelationGraph(QWidget):
    """Lightweight relation graph (Customer -> Invoice -> Approval -> Payment)."""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)
        self.nodes = [] # List of (label, type, x, y)
        self.links = [] # List of (from_idx, to_idx)

    def set_workflow(self, workflow):
        """Build nodes based on workflow context."""
        self.nodes = []
        self.links = []
        if not workflow: return
        
        # Mocking logical flow for visualization
        self.nodes.append(("Entity", workflow.get('entity_type', 'System'), 50, 100))
        self.nodes.append(("Workflow", workflow.get('status', 'PENDING'), 200, 100))
        self.nodes.append(("Approver", workflow.get('assigned_to_name', 'User'), 350, 50))
        self.nodes.append(("Result", "Pending", 500, 100))
        
        self.links = [(0, 1), (1, 2), (2, 3)]
        self.update()

    def paintEvent(self, event):
        if not self.nodes: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Links
        painter.setPen(QPen(QColor(COLOR_TABLE_BORDER_LIGHT), 2))
        for start, end in self.links:
            n1 = self.nodes[start]
            n2 = self.nodes[end]
            painter.drawLine(n1[2] + 40, n1[3] + 20, n2[2], n2[3] + 20)
            
        # Draw Nodes
        for label, val, x, y in self.nodes:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(COLOR_BG_ELEVATED)))
            painter.drawRoundedRect(x, y, 100, 40, 8, 8)
            
            painter.setPen(QColor(COLOR_PRIMARY_MUTED))
            painter.setFont(QFont("Segoe UI", TEXT_TABLE_HEADER))
            painter.drawText(x + 5, y + 15, label)

            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont("Segoe UI", TEXT_TABLE_HEADER, QFont.Weight.Bold))
            painter.drawText(x + 5, y + 32, val)


class WorkflowIntelligenceScreen(BaseScreen):
    """Workflow Intelligence Screen - Live Decision Tracking."""
    
    def __init__(self, parent=None, screen_id="workflow_intelligence", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client or APIClient()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._load_data)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG + SPACING_XS)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Workflow Intelligence")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        
        self.status_label = QLabel("LIVE TRACKING ACTIVE")
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_VALID}; font-weight: 700; font-size: {TEXT_BODY}pt; background: {COLOR_TABLE_HEADER_BG_LIGHT}; padding: {SPACING_XS}px 10px; border-radius: {BORDER_RADIUS_SM};")
        
        header.addWidget(title)
        header.addWidget(self.status_label)
        header.addStretch()
        
        refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        refresh_btn.clicked.connect(self._load_data)
        header.addWidget(refresh_btn)
        layout.addLayout(header)
        
        # Pipeline View
        self.pipeline = WorkflowPipelineWidget()
        layout.addWidget(self.pipeline)
        
        # Main Grid
        grid = QGridLayout()
        grid.setSpacing(SPACING_LG + SPACING_XS)
        
        # 1. Active Decisions (Left)
        active_group = self._create_group("Live Decisions Pipeline", 400)
        self.active_table = self._create_table(["Entity", "Reference", "State", "Approver", "Age"])
        active_group.layout().addWidget(self.active_table)
        grid.addWidget(active_group, 0, 0)
        
        # 2. Bottlenecks (Right)
        bottleneck_group = self._create_group("Bottlenecks & Delays", 400)
        self.bottleneck_list = QListWidget()
        self.bottleneck_list.setStyleSheet(f"background: {COLOR_BG_SURFACE}; border: none; border-radius: {BORDER_RADIUS_LG};")
        bottleneck_group.layout().addWidget(self.bottleneck_list)
        grid.addWidget(bottleneck_group, 0, 1)
        
        # 3. Relation Graph (Bottom Left)
        graph_group = self._create_group("Decision Flow Graph", 300)
        self.graph = WorkflowRelationGraph()
        graph_group.layout().addWidget(self.graph)
        grid.addWidget(graph_group, 1, 0)
        
        # 4. Load Analytics (Bottom Right)
        load_group = self._create_group("Approval Load Analytics", 300)
        self.load_table = self._create_table(["Approver", "Pending", "Avg Time", "Load %"])
        load_group.layout().addWidget(self.load_table)
        grid.addWidget(load_group, 1, 1)
        
        layout.addLayout(grid)

    def _create_group(self, title, min_h):
        group = QGroupBox(title)
        group.setMinimumHeight(min_h)
        group.setStyleSheet(f"QGroupBox {{ color: {COLOR_PRIMARY}; font-weight: bold; border: 1px solid {COLOR_TABLE_HEADER_BG_LIGHT}; border-radius: {BORDER_RADIUS_XL}; margin-top: 15px; background: {COLOR_BG_MAIN}; }} QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 {MARGIN_VERTICAL_SM}px; }}")
        QVBoxLayout(group)
        group.layout().setContentsMargins(SPACING_MD,  SPACING_XL + SPACING_SM,  SPACING_MD,  SPACING_MD)
        return group

    def _create_table(self, headers):
        columns = [TableColumn(k, h) for k, h in zip([f"col{i}" for i in range(len(headers))], headers)]
        table = EnterpriseTable(columns)
        table.verticalHeader().setVisible(False)
        return table

    def _on_screen_shown(self):
        self._load_data()
        self._refresh_timer.start(15000)
        register_timer("workflow_intel", self._refresh_timer)

    def _on_screen_hidden(self):
        self._refresh_timer.stop()

    def _load_data(self):
        """Fetch all workflow data through existing APIs."""
        try:
            # 1. Load instances
            response = self._api_client.get('/api/workflows/instances/')
            if response and response.get('success'):
                instances = response.get('data', [])
                if isinstance(instances, dict): instances = instances.get('results', [])
                self._update_ui(instances)
            else:
                self.status_label.setText("CONNECTION ERROR")
                self.status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold; font-size: {TEXT_BODY}px; background: {COLOR_BORDER}; padding: {SPACING_XS}px 10px; border-radius: {BORDER_RADIUS_SM};")
        except Exception as e:
            print(f"Workflow fetch error: {e}")

    def _update_ui(self, instances):
        self.status_label.setText("LIVE TRACKING ACTIVE")
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_VALID}; font-weight: 700; font-size: {TEXT_BODY}pt; background: {COLOR_BORDER}; padding: {SPACING_XS}px 10px; border-radius: {BORDER_RADIUS_SM};")
        
        # Update Pipeline
        counts = {'DRAFT': 0, 'PENDING_APPROVAL': 0, 'APPROVED': 0, 'REJECTED': 0, 'POSTED': 0}
        for inst in instances:
            state = inst.get('current_state')
            if state in counts: counts[state] += 1
        self.pipeline.set_data(counts)
        
        # Update Active Table (use set_data with EnterpriseTable)
        active_data = []
        for inst in instances[:20]:
            created_at = inst.get('created_at', '')[:19]
            try:
                dt = datetime.fromisoformat(created_at)
                age = str(datetime.now() - dt).split('.')[0]
            except (ValueError, TypeError):
                age = "Unknown"
            active_data.append({
                "col0": inst.get('content_type', ''),
                "col1": inst.get('object_reference', ''),
                "col2": inst.get('current_state', ''),
                "col3": inst.get('pending_approver_name', 'System'),
                "col4": age,
            })
        self.active_table.set_data(active_data)

        # Detect Bottlenecks
        self.bottleneck_list.clear()
        for inst in instances:
            state = inst.get('current_state')
            if state == 'PENDING_APPROVAL':
                created_at = inst.get('created_at', '')[:19]
                try:
                    dt = datetime.fromisoformat(created_at)
                    if datetime.now() - dt > timedelta(hours=24):
                        item = QListWidgetItem(f"🚨 CRITICAL: {inst.get('object_reference')} stuck for > 24h")
                        item.setForeground(QColor(COLOR_DANGER))
                        self.bottleneck_list.addItem(item)
                    elif datetime.now() - dt > timedelta(hours=6):
                        item = QListWidgetItem(f"⚠️ WARNING: {inst.get('object_reference')} pending for > 6h")
                        item.setForeground(QColor(COLOR_WARNING))
                        self.bottleneck_list.addItem(item)
                except Exception:
                    pass
        
        if self.bottleneck_list.count() == 0:
            self.bottleneck_list.addItem("No workflow bottlenecks detected.")
            
        # Update Load Analytics (Simplified)
        approvers = {}
        for inst in instances:
            if inst.get('current_state') == 'PENDING_APPROVAL':
                user = inst.get('pending_approver_name', 'System')
                approvers[user] = approvers.get(user, 0) + 1
        
        load_data = [{"col0": user, "col1": str(count), "col2": "~2.5h"} for user, count in approvers.items()]
        self.load_table.set_data(load_data)
        
        # Select first for graph
        if instances: self.graph.set_workflow(instances[0])
