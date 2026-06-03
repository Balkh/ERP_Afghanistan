"""Navigation history data structure for MainWindow.

Extracted from ui/main_window.py in Phase 5 Workstream C as the
Priority 1 (P1) data-only extraction. Behavior is preserved 1:1
with the original inline state previously stored on MainWindow.

The original code stored three pieces of state on MainWindow:
    self.navigation_history = []        # List[Tuple[int, str]]
    self._max_history = 20              # int
    self._disable_history = False       # bool

This class encapsulates that state with a small, well-defined API:
    push(index, title) -> None         # Append with dedup + bound
    pop() -> Optional[Tuple[int, str]] # Pop most recent
    __bool__() -> bool                 # Non-empty check
    __len__() -> int                   # Size check
    disabled (property)                # Reentrancy guard

No Qt dependency. No signals. No threading. Pure data structure.
"""

from typing import List, Optional, Tuple


class NavigationHistory:
    """Bounded stack of visited pages for back-navigation.

    Maintains a deduplicated, bounded stack of (index, title) tuples
    representing pages the user has visited. The stack is consulted
    by the back / home navigation methods to determine where to
    navigate next.
    """

    DEFAULT_MAX_HISTORY = 20

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY):
        if max_history < 1:
            raise ValueError("max_history must be >= 1")
        self._stack: List[Tuple[int, str]] = []
        self._max_history = max_history
        self._disabled = False

    # ── Stack operations ─────────────────────────────────────────

    def push(self, index: int, title: str) -> None:
        """Append a page entry to the history.

        Behavior (preserved 1:1 with original code):
        - If ``disabled`` is True, the call is a no-op.
        - If the top of stack is the same ``index``, the call is a no-op
          (consecutive duplicate suppression).
        - Otherwise append, then trim to ``max_history`` most-recent
          entries.
        """
        if self._disabled:
            return
        if self._stack and self._stack[-1][0] == index:
            return
        self._stack.append((index, title))
        if len(self._stack) > self._max_history:
            self._stack = self._stack[-self._max_history:]

    def pop(self) -> Optional[Tuple[int, str]]:
        """Remove and return the most recent entry.

        Returns ``None`` if the stack is empty (preserves the original
        truthy-check pattern: ``if self.navigation_history:``).
        """
        if not self._stack:
            return None
        return self._stack.pop()

    def peek(self) -> Optional[Tuple[int, str]]:
        """Return the most recent entry without removing it.

        Returns ``None`` if the stack is empty.
        """
        if not self._stack:
            return None
        return self._stack[-1]

    def clear(self) -> None:
        """Remove all entries from the stack."""
        self._stack.clear()

    def __getitem__(self, index):
        """Index access for backward compatibility with list patterns.

        Supports negative indices (``[-1]``) and slices (``[-N:]``).
        Direct mutations via ``__setitem__`` are intentionally not
        supported; use :meth:`push` instead.
        """
        return self._stack[index]

    # ── Dunder methods (preserve original usage patterns) ──────

    def __bool__(self) -> bool:
        """True if history is non-empty.

        Allows ``if self.navigation_history:`` to keep working
        unchanged after extraction.
        """
        return bool(self._stack)

    def __len__(self) -> int:
        return len(self._stack)

    # ── Disabled flag (reentrancy guard) ────────────────────────

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = bool(value)

    def __repr__(self) -> str:
        return (
            f"NavigationHistory(max_history={self._max_history}, "
            f"size={len(self._stack)}, disabled={self._disabled})"
        )
