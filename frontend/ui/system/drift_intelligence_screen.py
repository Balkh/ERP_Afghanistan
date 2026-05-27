"""
Drift Intelligence Screen - Predictive ERP Integrity Dashboard.
Visualizes system drift, risk heatmaps, and predictive warnings.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QListWidget, QListWidgetItem, QGroupBox)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_VERTICAL_SM, TEXT_SECTION_TITLE, TEXT_BODY,
                           TEXT_HELPER, BORDER_RADIUS_SM, BORDER_RADIUS_LG, BORDER_RADIUS_XL, COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED,
                           COLOR_TEXT_PRIMARY, COLOR_PRIMARY, COLOR_SUCCESS,
                           COLOR_WARNING, COLOR_DANGER, TEXT_TABLE, COLOR_STATUS_VALID,
                           COLOR_INFO)
from api.drift_intelligence_service import DriftIntelligenceService

class DriftGaugeWidget(QWidget):
    """Circular gauge for displaying Drift Score."""
    def __init__(self, title):
        super().__init__()
        self.setFixedSize(150, 150)
        self.title = title
        self.score = 0
        self.color = COLOR_SUCCESS

    def set_score(self, score):
        self.score = score
        if score > 70: self.color = COLOR_DANGER
        elif score > 30: self.color = COLOR_WARNING
        else: self.color = COLOR_SUCCESS
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(10, 10, -10, -10)
        
        # Draw Background Circle
        painter.setPen(QPen(QColor(COLOR_BG_ELEVATED), 8))
        painter.drawArc(rect, -45 * 16, 270 * 16)
        
        # Draw Score Arc
        painter.setPen(QPen(QColor(self.color), 10))
        span_angle = int((self.score / 100.0) * 270 * 16)
        painter.drawArc(rect, 225 * 16, -span_angle)
        
        # Draw Text
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        painter.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{self.score}%")

        painter.setFont(QFont("Segoe UI", TEXT_HELPER))
        painter.drawText(0, self.height() - 15, self.width(), 15, Qt.AlignCenter, self.title)

class RiskHeatmapWidget(QWidget):
    """Grid-based heatmap for module risk levels."""
    def __init__(self, modules):
        super().__init__()
        self.setFixedHeight(120)
        self.modules = modules
        self.risk_data = {m: "LOW" for m in modules}

    def set_data(self, risk_data):
        self.risk_data.update(risk_data)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        cell_w = (w - 20) / len(self.modules)
        
        for i, mod in enumerate(self.modules):
            risk = self.risk_data.get(mod, "LOW")
            color = COLOR_SUCCESS
            if risk == "CRITICAL": color = COLOR_DANGER
            elif risk == "HIGH": color = COLOR_WARNING
            elif risk == "MEDIUM": color = COLOR_WARNING
            
            x = 10 + i * cell_w
            __rect = QPointF(x, 10), QPointF(x + cell_w - 5, 60)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(color)))
            painter.drawRoundedRect(int(x), 10, int(cell_w - 5), 50, 5, 5)
            
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont("Segoe UI", TEXT_TABLE, QFont.Weight.Bold))
            painter.drawText(int(x), 75, int(cell_w - 5), 15, Qt.AlignCenter, mod)

class DriftIntelligenceScreen(BaseScreen):
    """Drift Intelligence Dashboard - Predictive System Analytics."""
    
    def __init__(self, parent=None, screen_id="drift_intelligence", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._drift_service = DriftIntelligenceService()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM)
        layout.setSpacing(SPACING_LG + SPACING_XS)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("System Drift Intelligence")
        title_font = QFont("Segoe UI", TEXT_SECTION_TITLE)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        
        self.status_badge = QLabel("PREDICTIVE ANALYSIS ACTIVE")
        self.status_badge.setStyleSheet(f"color: {COLOR_STATUS_VALID}; font-weight: bold; font-size: {TEXT_BODY}px; background: {COLOR_BG_ELEVATED}; padding: {SPACING_XS}px 10px; border-radius: {BORDER_RADIUS_SM};")
        
        header.addWidget(title)
        header.addWidget(self.status_badge)
        header.addStretch()
        layout.addLayout(header)
        
        # Main Dashboard Grid
        grid = QGridLayout()
        grid.setSpacing(SPACING_LG + SPACING_XS)
        
        # 1. Overall Drift Gauge (Top Left)
        gauge_group = self._create_group("System-Wide Drift Score", 200)
        self.main_gauge = DriftGaugeWidget("Overall Drift")
        gauge_group.layout().addWidget(self.main_gauge, 0, Qt.AlignCenter)
        grid.addWidget(gauge_group, 0, 0)
        
        # 2. Risk Heatmap (Top Right)
        heatmap_group = self._create_group("Module Risk Heatmap", 200)
        self.heatmap = RiskHeatmapWidget(self._drift_service.modules)
        heatmap_group.layout().addWidget(self.heatmap)
        grid.addWidget(heatmap_group, 0, 1)
        
        # 3. Early Warning Panel (Bottom Left)
        warning_group = self._create_group("Early Warnings & Drift Patterns", 400)
        self.warning_list = QListWidget()
        self.warning_list.setStyleSheet(f"background: {COLOR_BG_SURFACE}; border: none; border-radius: {BORDER_RADIUS_LG};")
        warning_group.layout().addWidget(self.warning_list)
        grid.addWidget(warning_group, 1, 0)
        
        # 4. Detailed Module Drift (Bottom Right)
        detail_group = self._create_group("Module Drift Analysis", 400)
        self.detail_list = QListWidget()
        self.detail_list.setStyleSheet(self.warning_list.styleSheet())
        detail_group.layout().addWidget(self.detail_list)
        grid.addWidget(detail_group, 1, 1)
        
        layout.addLayout(grid)

    def _create_group(self, title, min_h):
        group = QGroupBox(title)
        group.setMinimumHeight(min_h)
        group.setStyleSheet(f"QGroupBox {{ color: {COLOR_PRIMARY}; font-weight: bold; border: 1px solid {COLOR_BG_ELEVATED}; border-radius: {BORDER_RADIUS_XL}; margin-top: 15px; background: {COLOR_BG_MAIN}; }} QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 {MARGIN_VERTICAL_SM}px; }}")
        QVBoxLayout(group)
        group.layout().setContentsMargins(SPACING_MD,  SPACING_XL + SPACING_SM,  SPACING_MD,  SPACING_MD)
        return group

    def process_integrity_results(self, results):
        """Consume integrity scan results and update drift intelligence."""
        self._drift_service.add_snapshot(results)
        analysis = self._drift_service.calculate_drift_intelligence()
        
        if analysis.get('status') == 'insufficient_data':
            self._show_empty_state()
            return
            
        self._update_ui(analysis)

    def _show_empty_state(self):
        self.warning_list.clear()
        self.warning_list.addItem("Waiting for more system scans to establish baseline...")
        self.main_gauge.set_score(0)

    def _update_ui(self, analysis):
        # Update Gauge
        self.main_gauge.set_score(analysis["overall_drift_score"])
        
        # Update Heatmap
        self.heatmap.set_data(analysis["risk_heatmap"])
        
        # Update Warnings
        self.warning_list.clear()
        if not analysis["warnings"]:
            item = QListWidgetItem("✅ System stable - No drift patterns detected.")
            item.setForeground(QColor(COLOR_SUCCESS))
            self.warning_list.addItem(item)
        else:
            for warn in analysis["warnings"]:
                item = QListWidgetItem(f"⚠️ {warn}")
                item.setForeground(QColor(COLOR_WARNING))
                self.warning_list.addItem(item)

        # Update Detailed Analysis
        self.detail_list.clear()
        for mod, data in analysis["module_drift"].items():
            trend_icon = "→"
            color = COLOR_INFO
            if data["trend"] == "UP": 
                trend_icon = "↑"
                color = COLOR_DANGER
            elif data["trend"] == "DOWN":
                trend_icon = "↓"
                color = COLOR_SUCCESS
                
            text = f"{mod}: Drift {data['score']}% {trend_icon} | {data['pattern']}"
            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            self.detail_list.addItem(item)

    def _on_screen_shown(self):
        # Check if we have data to show
        analysis = self._drift_service.calculate_drift_intelligence()
        if analysis.get('status') != 'insufficient_data':
            self._update_ui(analysis)
        else:
            self._show_empty_state()
