from ui.constants import (COLOR_PRIMARY, TEXT_BODY)
"""Loading spinner component for ERP."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPainter, QColor, QPen


class LoadingSpinner(QWidget):
    """Circular loading spinner."""
    
    def __init__(self, size=40, color=COLOR_PRIMARY, parent=None):
        super().__init__(parent)
        self.size = size
        self.color = QColor(color)
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        self.setFixedSize(size, size)
        
    def start(self):
        """Start the spinner animation."""
        self.timer.start(50)  # Update every 50ms
        self.show()
        
    def stop(self):
        """Stop the spinner animation."""
        self.timer.stop()
        self.hide()
        
    def rotate(self):
        """Rotate the spinner."""
        self.angle = (self.angle + 10) % 360
        self.update()
        
    def paintEvent(self, event):
        """Paint the spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set up pen
        pen = QPen(self.color, 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # Draw arc
        rect = QRect(2, 2, self.size - 4, self.size - 4)
        span_angle = int(270 * 16)  # 270 degrees in 1/16th of a degree
        start_angle = int(self.angle * 16)  # Convert to 1/16th of a degree
        painter.drawArc(rect, start_angle, span_angle)


class LoadingOverlay(QWidget):
    """Full-screen loading overlay."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.spinner = LoadingSpinner(size=60, color=COLOR_PRIMARY)
        layout.addWidget(self.spinner)
        
        self.label = QLabel("Loading...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_PRIMARY};
                font-size: {TEXT_BODY}px;
                margin-top: 10px;
            }}
        """)
        layout.addWidget(self.label)
        
    def show_overlay(self, text="Loading..."):
        """Show the loading overlay."""
        self.label.setText(text)
        self.spinner.start()
        self.show()
        self.raise_()
        
    def hide_overlay(self):
        """Hide the loading overlay."""
        self.spinner.stop()
        self.hide()