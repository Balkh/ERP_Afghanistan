"""
Performance and Stability Testing Module.
Measures UI responsiveness, memory usage, and long-running stability.
"""

import pytest
import time
import tracemalloc
import gc
from unittest.mock import MagicMock
from typing import Dict, List, Any, Callable
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest


class PerformanceMetrics:
    """Container for performance metrics."""
    
    def __init__(self):
        self.render_time_ms: float = 0.0
        self.memory_mb: float = 0.0
        self.cpu_time_ms: float = 0.0
        self.operation_count: int = 0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'render_time_ms': self.render_time_ms,
            'memory_mb': self.memory_mb,
            'cpu_time_ms': self.cpu_time_ms,
            'operation_count': self.operation_count
        }
    
    def __repr__(self):
        return f"PerformanceMetrics(render={self.render_time_ms:.2f}ms, memory={self.memory_mb:.2f}MB)"


class PerformanceTester:
    """Performance testing utilities for UI components."""
    
    @staticmethod
    def measure_widget_render(widget: QWidget) -> float:
        """Measure widget render time in milliseconds."""
        widget.show()
        QApplication.processEvents()
        
        start = time.perf_counter()
        widget.repaint()
        QApplication.processEvents()
        end = time.perf_counter()
        
        return (end - start) * 1000
    
    @staticmethod
    def measure_memory_usage(func: Callable, iterations: int = 10) -> Dict[str, float]:
        """Measure memory usage of a function."""
        tracemalloc.start()
        
        gc.collect()
        initial = tracemalloc.get_traced_memory()[0]
        
        for _ in range(iterations):
            func()
            
        gc.collect()
        final = tracemalloc.get_traced_memory()[0]
        
        tracemalloc.stop()
        
        return {
            'initial_mb': initial / 1024 / 1024,
            'final_mb': final / 1024 / 1024,
            'delta_mb': (final - initial) / 1024 / 1024,
            'avg_per_iteration_mb': (final - initial) / 1024 / 1024 / iterations
        }
    
    @staticmethod
    def measure_table_operations(table, data: List[Dict]) -> Dict[str, float]:
        """Measure table operations performance."""
        results = {}
        
        # Measure data loading
        start = time.perf_counter()
        table.set_data(data)
        QApplication.processEvents()
        results['load_time_ms'] = (time.perf_counter() - start) * 1000
        
        # Measure selection
        start = time.perf_counter()
        if table.rowCount() > 0:
            table.selectRow(0)
        QApplication.processEvents()
        results['selection_time_ms'] = (time.perf_counter() - start) * 1000
        
        # Measure sorting
        start = time.perf_counter()
        if table.columnCount() > 0:
            table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        QApplication.processEvents()
        results['sort_time_ms'] = (time.perf_counter() - start) * 1000
        
        return results
    
    @staticmethod
    def measure_form_operations(form, data: Dict) -> Dict[str, float]:
        """Measure form operations performance."""
        results = {}
        
        # Measure data setting
        start = time.perf_counter()
        form.set_data(data)
        QApplication.processEvents()
        results['set_data_time_ms'] = (time.perf_counter() - start) * 1000
        
        # Measure validation
        start = time.perf_counter()
        form.validate()
        QApplication.processEvents()
        results['validation_time_ms'] = (time.perf_counter() - start) * 1000
        
        return results


class StabilityTester:
    """Stability testing for long-running UI sessions."""
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.cycle_count = 0
        self.error_count = 0
        self.errors: List[str] = []
        
    def simulate_cycles(self, cycles: int, operation: Callable):
        """Simulate repeated operation cycles."""
        for i in range(cycles):
            try:
                operation()
                self.cycle_count += 1
                QApplication.processEvents()
            except Exception as e:
                self.error_count += 1
                self.errors.append(f"Cycle {i}: {str(e)}")
                
    def get_stability_report(self) -> Dict[str, Any]:
        """Get stability report."""
        success_rate = ((self.cycle_count - self.error_count) / self.cycle_count * 100) if self.cycle_count > 0 else 0
        
        return {
            'total_cycles': self.cycle_count,
            'error_count': self.error_count,
            'success_rate_percent': success_rate,
            'errors': self.errors[:10]  # First 10 errors
        }


class MemoryLeakTester:
    """Test for memory leaks in UI components."""
    
    @staticmethod
    def test_widget_memory_leak(qtbot, widget_factory: Callable) -> Dict[str, Any]:
        """Test widget for memory leaks."""
        tracemalloc.start()
        
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create and destroy widget multiple times
        for _ in range(10):
            widget = widget_factory()
            qtbot.addWidget(widget)
            widget.close()
            widget.deleteLater()
            
        gc.collect()
        final_objects = len(gc.get_objects())
        
        tracemalloc.stop()
        
        return {
            'initial_objects': initial_objects,
            'final_objects': final_objects,
            'leaked_objects': final_objects - initial_objects,
            'has_leak': final_objects > initial_objects + 10
        }
    
    @staticmethod
    def test_qwidget_cleanup(qtbot):
        """Test QWidget cleanup."""
        from PySide6.QtWidgets import QPushButton
        
        initial_count = QPushButton.instanceCount()
        
        buttons = []
        for _ in range(10):
            btn = QPushButton("Test")
            buttons.append(btn)
            
        for btn in buttons:
            btn.deleteLater()
            
        QApplication.processEvents()
        
        # Allow Qt to clean up
        gc.collect()
        
        return {
            'instances_created': 10,
            'leaked': QPushButton.instanceCount() - initial_count > 5
        }


class LargeDatasetTester:
    """Test UI with large datasets."""
    
    @staticmethod
    def generate_test_data(rows: int) -> List[Dict]:
        """Generate test data for large dataset testing."""
        return [
            {
                'id': i,
                'name': f'Product {i}',
                'code': f'PROD-{i:05d}',
                'price': (i % 100) * 10.50,
                'quantity': i % 50,
                'status': 'active' if i % 2 == 0 else 'inactive'
            }
            for i in range(1, rows + 1)
        ]
    
    @staticmethod
    def test_table_with_large_data(qtbot, table, row_count: int) -> Dict[str, Any]:
        """Test table performance with large dataset."""
        data = LargeDatasetTester.generate_test_data(row_count)
        
        # Measure load time
        start = time.perf_counter()
        table.set_data(data)
        QApplication.processEvents()
        load_time = (time.perf_counter() - start) * 1000
        
        # Measure scroll performance (approximation)
        start = time.perf_counter()
        if table.rowCount() > 0:
            table.scrollToItem(table.item(row_count - 1, 0))
        QApplication.processEvents()
        scroll_time = (time.perf_counter() - start) * 1000
        
        # Measure search/filter performance
        start = time.perf_counter()
        table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        QApplication.processEvents()
        sort_time = (time.perf_counter() - start) * 1000
        
        return {
            'row_count': row_count,
            'load_time_ms': load_time,
            'scroll_time_ms': scroll_time,
            'sort_time_ms': sort_time,
            'avg_time_per_row_ms': load_time / row_count
        }
    
    @staticmethod
    def test_form_with_many_fields() -> float:
        """Test form performance with many fields."""
        from ui.components.forms import EnterpriseForm, FieldType
        
        form = EnterpriseForm()
        
        # Add many fields
        start = time.perf_counter()
        for i in range(50):
            form.add_field(
                f"field_{i}",
                FieldType.TEXT,
                f"Field {i}",
                required=False
            )
        creation_time = (time.perf_counter() - start) * 1000
        
        return creation_time


class StressTester:
    """Stress testing for UI components."""
    
    @staticmethod
    def stress_test_button_clicks(qtbot, button, count: int) -> Dict[str, Any]:
        """Stress test button clicks."""
        click_count = [0]
        
        def on_click():
            click_count[0] += 1
            
        button.clicked.connect(on_click)
        
        start = time.perf_counter()
        
        for _ in range(count):
            qtbot.click(button)
            
        elapsed = time.perf_counter() - start
        
        return {
            'clicks': click_count[0],
            'target_clicks': count,
            'elapsed_seconds': elapsed,
            'clicks_per_second': click_count[0] / elapsed if elapsed > 0 else 0
        }
    
    @staticmethod
    def stress_test_text_input(qtbot, line_edit, text: str, iterations: int) -> Dict[str, Any]:
        """Stress test text input."""
        start = time.perf_counter()
        
        for _ in range(iterations):
            line_edit.clear()
            line_edit.setText(text)
            QApplication.processEvents()
            
        elapsed = time.perf_counter() - start
        
        return {
            'iterations': iterations,
            'elapsed_seconds': elapsed,
            'ops_per_second': iterations / elapsed if elapsed > 0 else 0
        }


# Pytest test classes

class TestPerformanceMetrics:
    """Test performance measurement."""
    
    def test_performance_metrics_creation(self):
        """Test metrics object creation."""
        metrics = PerformanceMetrics()
        
        assert metrics.render_time_ms == 0.0
        assert metrics.memory_mb == 0.0
        
    def test_performance_metrics_to_dict(self):
        """Test metrics to dictionary."""
        metrics = PerformanceMetrics()
        metrics.render_time_ms = 10.5
        
        d = metrics.to_dict()
        
        assert 'render_time_ms' in d
        assert d['render_time_ms'] == 10.5


class TestLargeDatasetPerformance:
    """Test performance with large datasets."""
    
    def test_data_generation(self):
        """Test generating test data."""
        data = LargeDatasetTester.generate_test_data(100)
        
        assert len(data) == 100
        assert data[0]['id'] == 1
        assert 'name' in data[0]
        
    def test_data_generation_1000_rows(self):
        """Test generating 1000 rows."""
        data = LargeDatasetTester.generate_test_data(1000)
        
        assert len(data) == 1000


class TestStability:
    """Test UI stability."""
    
    def test_stability_report(self):
        """Test stability report generation."""
        widget = QWidget()
        tester = StabilityTester(widget)
        
        # Simulate some cycles
        for i in range(10):
            tester.cycle_count += 1
            
        report = tester.get_stability_report()
        
        assert report['total_cycles'] == 10
        assert report['success_rate_percent'] == 100.0


class TestMemoryLeaks:
    """Test for memory leaks."""
    
    def test_memory_tester_exists(self):
        """Test memory leak tester exists."""
        assert hasattr(MemoryLeakTester, 'test_widget_memory_leak')


class TestStressTesting:
    """Test stress testing."""
    
    def test_stress_tester_exists(self):
        """Test stress tester exists."""
        assert hasattr(StressTester, 'stress_test_button_clicks')
        assert hasattr(StressTester, 'stress_test_text_input')