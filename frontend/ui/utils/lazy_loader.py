from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from typing import Dict, Any, Callable, Optional
from ui.constants import TEXT_BODY


class ScreenFactory:
    def __init__(self, builder: Callable, api_client=None, *args, **kwargs):
        self._builder = builder
        self._api_client = api_client
        self._args = args
        self._kwargs = kwargs
        self._instance = None

    def get(self) -> QWidget:
        if self._instance is None:
            self._instance = self._builder(api_client=self._api_client, *self._args, **self._kwargs)
        return self._instance

    def loaded(self) -> bool:
        return self._instance is not None

    def reset(self):
        self._instance = None


class LazyScreenManager:
    def __init__(self, stack, api_client=None):
        self._stack = stack
        self._api_client = api_client
        self._factories: Dict[int, ScreenFactory] = {}
        self._placeholders: Dict[int, int] = {}
        self._active_indices: Dict[int, int] = {}

    def register(self, index: int, builder: Callable, label: str = "Loading..."):
        placeholder = self._make_placeholder(label)
        self._stack.insertWidget(index, placeholder)
        self._factories[index] = ScreenFactory(builder, api_client=self._api_client)
        self._placeholders[index] = self._stack.indexOf(placeholder)

    def load(self, index: int) -> Optional[QWidget]:
        factory = self._factories.get(index)
        if factory is None:
            return None
        screen = factory.get()
        placeholder_index = self._placeholders.get(index)
        if placeholder_index is not None and self._stack.widget(placeholder_index) is not None:
            self._stack.removeWidget(self._stack.widget(placeholder_index))
            del self._placeholders[index]
        current = self._stack.indexOf(screen)
        if current == -1:
            self._stack.insertWidget(index, screen)
            self._active_indices[index] = index
        return screen

    def get(self, index: int) -> Optional[QWidget]:
        factory = self._factories.get(index)
        if factory is None:
            return None
        if not factory.loaded():
            return None
        return factory.get()

    def is_loaded(self, index: int) -> bool:
        factory = self._factories.get(index)
        return factory is not None and factory.loaded()

    def reset_all(self):
        for factory in self._factories.values():
            factory.reset()
        self._placeholders.clear()
        self._active_indices.clear()

    @staticmethod
    def _make_placeholder(text: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: #6c7086; font-size: {TEXT_BODY}px;")
        layout.addWidget(label)
        return w
