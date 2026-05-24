"""
Phase UX.5 — Workflow Intelligence.

Rule-based, context-aware navigation suggestions and action memory.
NO AI, NO ML, NO external APIs — purely rule-driven.

Provides:
- RecentActionStore: In-memory action history (bounded, 100 entries)
- SuggestionEngine: Context-based next-action suggestions
- NavigationAccelerator: Shortcuts and hints based on workflow state
"""
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
import time


# ── Workflow Rules (canonical source) ──────────────────────────────
# Each rule maps a screen/action to suggested next actions.
# Rules are tuples of: (trigger_screen, suggested_screen, suggestion_label, priority)

_WORKFLOW_RULES: List[Tuple[str, str, str, int]] = [
    # Sales flow
    ("Sales Invoice",         "Customer Payments",    "Record payment for this invoice",     90),
    ("sales_invoice_saved",   "customer_payments",    "Payment pending for invoice",          85),
    ("Customers",             "Sales Invoice",        "Create invoice for this customer",     80),
    ("customers_opened",      "credit_warning",       "Check customer credit limit",          70),

    # Purchases flow
    ("Purchase Invoice",      "Supplier Payments",    "Record payment for this purchase",     90),
    ("purchase_invoice_saved","supplier_payments",    "Payment pending for purchase",         85),
    ("Suppliers",             "Purchase Invoice",     "Create purchase order",                80),

    # Accounting flow
    ("Chart of Accounts",     "Journal Entries",      "Post entry to this account",           75),
    ("Journal Entries",       "Account Ledger",       "View ledger for this entry",           70),
    ("Account Ledger",        "Trial Balance",        "Verify balance after ledger view",     65),
    ("Trial Balance",         "Profit & Loss",        "Review P&L after trial balance",       60),
    ("Profit & Loss",         "Balance Sheet",        "View balance sheet",                    55),

    # Returns flow
    ("Return Orders",         "Reconciliation",       "Reconcile this return",                85),
    ("Reconciliation",        "Returns Explainability","Review return explanation",           75),

    # Finance flow
    ("Payments",              "Cash Flow",            "Review cash impact",                   70),
    ("Expenses",              "Budgeting",            "Check budget vs actual",               65),
    ("Customer Payments",     "AR Ageing",            "View AR ageing after payment",         70),
    ("Supplier Payments",     "AP Ageing",            "View AP ageing after payment",         70),

    # HR flow
    ("Employees",             "Attendance",           "Record attendance for employee",       75),
    ("Attendance",            "Leave",                "Check leave balance",                  70),
    ("Leave",                 "Payroll",              "Process payroll after leave",          65),

    # System flow
    ("Backup & Restore",      "Audit Log",            "Verify backup in audit log",           60),
    ("User Management",       "Role Management",      "Assign roles to user",                 75),
]

# Actions that follow a workflow pattern (sorted by priority)
_WORKFLOW_CHAINS: Dict[str, List[Tuple[str, int]]] = {
    "sales": [
        ("customers", 10), ("sales_invoice", 20), ("customer_payments", 30),
        ("ar_ageing", 40),
    ],
    "purchases": [
        ("suppliers", 10), ("purchase_invoice", 20), ("supplier_payments", 30),
        ("ap_ageing", 40),
    ],
    "accounting_close": [
        ("journal_entries", 10), ("account_ledger", 20), ("trial_balance", 30),
        ("profit_loss", 40), ("balance_sheet", 50),
    ],
    "hr_cycle": [
        ("employees", 10), ("attendance", 20), ("leave", 30), ("payroll", 40),
    ],
}


class RecentActionStore:
    """Bounded, in-memory store of recent user actions."""

    def __init__(self, max_actions: int = 100):
        self._actions: deque = deque(maxlen=max_actions)
        self._screen_visits: Dict[str, int] = defaultdict(int)
        self._last_action: Optional[str] = None
        self._last_screen: Optional[str] = None

    def record_action(self, action: str, screen: str, metadata: Optional[Dict] = None):
        now = time.time()
        entry = {
            'action': action,
            'screen': screen,
            'metadata': metadata or {},
            'ts': now,
        }
        self._actions.append(entry)
        self._screen_visits[screen] += 1
        self._last_action = action
        self._last_screen = screen

    def record_navigation(self, screen: str):
        self.record_action('navigate', screen)

    def last_action(self) -> Optional[str]:
        return self._last_action

    def last_screen(self) -> Optional[str]:
        return self._last_screen

    def screen_visit_count(self, screen: str) -> int:
        return self._screen_visits.get(screen, 0)

    def recent_actions(self, count: int = 10) -> List[Dict]:
        return list(self._actions)[-count:]

    def workflow_position(self, chain_name: str) -> int:
        """Return current position in a workflow chain (0=not started)."""
        chain = _WORKFLOW_CHAINS.get(chain_name, [])
        for step_name, step_order in reversed(chain):
            if self.screen_visit_count(step_name) > 0:
                return step_order
        return 0

    def get_context(self) -> Dict[str, Any]:
        return {
            'last_screen': self._last_screen,
            'last_action': self._last_action,
            'frequent_screens': sorted(
                self._screen_visits.items(), key=lambda x: -x[1]
            )[:5],
        }


class SuggestionEngine:
    """Rule-based next-action suggestion engine."""

    def __init__(self, action_store: RecentActionStore):
        self._store = action_store

    def get_suggestions(self, current_screen: str, max_suggestions: int = 3) -> List[Dict]:
        suggestions: List[Dict] = []

        # Direct rules matching current screen
        for trigger, suggested, label, priority in _WORKFLOW_RULES:
            if trigger == current_screen:
                suggestions.append({
                    'target': suggested,
                    'label': label,
                    'priority': priority,
                    'type': 'direct',
                })

        # Workflow chain progression
        for chain_name, steps in _WORKFLOW_CHAINS.items():
            pos = self._store.workflow_position(chain_name)
            for step_name, step_order in steps:
                if step_order > pos:
                    suggestions.append({
                        'target': step_name,
                        'label': f"Continue {chain_name}: {step_name.replace('_', ' ').title()}",
                        'priority': max(50, 100 - step_order),
                        'type': 'chain',
                    })
                    break

        # Deduplicate by target, keep highest priority
        seen: Dict[str, Dict] = {}
        for s in suggestions:
            target = s['target']
            if target not in seen or s['priority'] > seen[target]['priority']:
                seen[target] = s

        sorted_suggestions = sorted(seen.values(), key=lambda x: -x['priority'])
        return sorted_suggestions[:max_suggestions]

    def get_quick_nav_hints(self, current_screen: str) -> List[str]:
        """Return simple text hints for keyboard navigation."""
        hints = []
        for trigger, suggested, _, priority in _WORKFLOW_RULES:
            if trigger == current_screen and priority >= 70:
                hints.append(
                    f"Alt+{suggested[0].upper()}: Go to {suggested.replace('_', ' ').title()}"
                )
        return hints[:3]


class NavigationAccelerator:
    """Context-aware navigation acceleration.

    Tracks frequent navigation patterns and suggests shorthand routes.
    """

    def __init__(self, action_store: RecentActionStore):
        self._store = action_store
        self._common_routes: Dict[Tuple[str, str], int] = defaultdict(int)

    def record_navigation(self, from_screen: str, to_screen: str):
        key = (from_screen, to_screen)
        self._common_routes[key] += 1

    def get_accelerated_routes(self, current_screen: str, max_routes: int = 3) -> List[Dict]:
        routes = [
            {'from': f, 'to': t, 'frequency': c}
            for (f, t), c in self._common_routes.items()
            if f == current_screen
        ]
        routes.sort(key=lambda x: -x['frequency'])
        return routes[:max_routes]

    def get_frequent_route(self, current_screen: str) -> Optional[str]:
        """Get the most common next screen after current_screen."""
        routes = self.get_accelerated_routes(current_screen, 1)
        return routes[0]['to'] if routes else None

    def get_keyboard_hint(self, current_screen: str) -> Optional[str]:
        route = self.get_frequent_route(current_screen)
        if route:
            return f"Frequently: press Ctrl+G to go to {route.replace('_', ' ').title()}"
        return None


_instance: Optional[RecentActionStore] = None
_suggestion_engine: Optional[SuggestionEngine] = None
_nav_accelerator: Optional[NavigationAccelerator] = None


def get_action_store() -> RecentActionStore:
    global _instance
    if _instance is None:
        _instance = RecentActionStore()
    return _instance


def get_suggestion_engine() -> SuggestionEngine:
    global _suggestion_engine, _instance
    if _suggestion_engine is None:
        _suggestion_engine = SuggestionEngine(get_action_store())
    return _suggestion_engine


def get_nav_accelerator() -> NavigationAccelerator:
    global _nav_accelerator, _instance
    if _nav_accelerator is None:
        _nav_accelerator = NavigationAccelerator(get_action_store())
    return _nav_accelerator


def record_navigation(screen: str):
    """Record a navigation event across all intelligence components."""
    store = get_action_store()
    store.record_navigation(screen)
    engine = get_suggestion_engine()
    accelerator = get_nav_accelerator()
    if store.last_screen() is not None:
        accelerator.record_navigation(str(store.last_screen()), screen)


def get_suggestions(current_screen: str, max_suggestions: int = 3) -> List[Dict]:
    return get_suggestion_engine().get_suggestions(current_screen, max_suggestions)


def get_hints(current_screen: str) -> List[str]:
    hints = get_suggestion_engine().get_quick_nav_hints(current_screen)
    kb = get_nav_accelerator().get_keyboard_hint(current_screen)
    if kb:
        hints.append(kb)
    return hints
