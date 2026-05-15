"""
Pharmacy Rules Engine — validates pharmacy-specific constraints during sales.
Handles expiry warnings, controlled substances, prescription requirements,
duplicate medicine detection, stock thresholds, and cold-chain markers.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple


class RuleSeverity:
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class PharmacyRule:
    """A single pharmacy rule with validation logic."""

    def __init__(self, code: str, message: str, severity: str,
                 is_blocking: bool = False):
        self.code = code
        self.message = message
        self.severity = severity
        self.is_blocking = is_blocking


class PharmacyRuleResult:
    """Result of a pharmacy rule check."""

    def __init__(self):
        self.alerts: List[PharmacyRule] = []
        self.blockers: List[PharmacyRule] = []
        self.approval_required: bool = False
        self.approval_reason: Optional[str] = None

    def add_alert(self, rule: PharmacyRule):
        if rule.is_blocking:
            self.blockers.append(rule)
        else:
            self.alerts.append(rule)
        if rule.code in ("CONTROLLED_SUBSTANCE", "LARGE_DISCOUNT",
                         "PRESCRIPTION_REQUIRED", "STOCKOUT"):
            self.approval_required = True
            self.approval_reason = rule.message

    @property
    def has_blockers(self) -> bool:
        return len(self.blockers) > 0

    @property
    def has_alerts(self) -> bool:
        return len(self.alerts) > 0

    def to_dict(self) -> Dict:
        return {
            "alerts": [{"code": a.code, "message": a.message, "severity": a.severity} for a in self.alerts],
            "blockers": [{"code": b.code, "message": b.message, "severity": b.severity} for b in self.blockers],
            "approval_required": self.approval_required,
            "approval_reason": self.approval_reason,
            "can_proceed": not self.has_blockers,
        }


class PharmacyRulesEngine:
    """
    Evaluates pharmacy rules for cart items and returns alerts/blockers.
    Used by POS screen before completing a sale.
    """

    EXPIRY_WARNING_DAYS = 90
    LOW_STOCK_THRESHOLD = 10
    MIN_BOX_SIZE = 1
    MAX_QTY_PER_PRODUCT = 100

    def validate_cart(self, cart_items: List[Dict],
                      customer_id: Optional[str] = None) -> PharmacyRuleResult:
        result = PharmacyRuleResult()

        product_names = set()
        generic_names = set()

        for item in cart_items:
            product_name = item.get("product_name", "")
            generic_name = item.get("generic_name", "")
            quantity = item.get("quantity", 0)
            max_stock = item.get("max_stock", 0)
            expiry = item.get("expiry_date", "")
            requires_prescription = item.get("requires_prescription", False)
            is_controlled = item.get("is_controlled", False)
            is_cold_chain = item.get("is_cold_chain", False)
            sale_price = item.get("price", 0)

            self._check_expiry(result, product_name, expiry)
            self._check_stock(result, product_name, quantity, max_stock)
            self._check_quantity_limits(result, product_name, quantity)
            self._check_prescription(result, product_name, requires_prescription)
            self._check_controlled(result, product_name, is_controlled)
            self._check_cold_chain(result, product_name, is_cold_chain)
            self._check_duplicate_medicine(result, product_name, generic_name,
                                           product_names, generic_names)

            product_names.add(product_name)
            if generic_name:
                generic_names.add(generic_name)

        return result

    def _check_expiry(self, result: PharmacyRuleResult,
                      product_name: str, expiry_str: str):
        if not expiry_str:
            return
        try:
            exp = date.fromisoformat(expiry_str)
            today = date.today()
            days_remaining = (exp - today).days

            if days_remaining < 0:
                result.add_alert(PharmacyRule(
                    "EXPIRED",
                    f"BLOCKED: {product_name} expired on {expiry_str}",
                    RuleSeverity.BLOCKER, is_blocking=True,
                ))
            elif days_remaining <= 30:
                result.add_alert(PharmacyRule(
                    "EXPIRING_CRITICAL",
                    f"{product_name} expires in {days_remaining} days ({expiry_str})",
                    RuleSeverity.WARNING,
                ))
            elif days_remaining <= self.EXPIRY_WARNING_DAYS:
                result.add_alert(PharmacyRule(
                    "EXPIRING_SOON",
                    f"{product_name} expires in {days_remaining} days ({expiry_str})",
                    RuleSeverity.INFO,
                ))
        except (ValueError, TypeError):
            pass

    def _check_stock(self, result: PharmacyRuleResult,
                     product_name: str, quantity: int, max_stock: Decimal):
        if max_stock <= 0:
            result.add_alert(PharmacyRule(
                "STOCKOUT",
                f"BLOCKED: {product_name} is out of stock",
                RuleSeverity.BLOCKER, is_blocking=True,
            ))
        elif max_stock < quantity:
            result.add_alert(PharmacyRule(
                "INSUFFICIENT_STOCK",
                f"BLOCKED: {product_name} only has {max_stock} units (requested {quantity})",
                RuleSeverity.BLOCKER, is_blocking=True,
            ))
        elif max_stock <= self.LOW_STOCK_THRESHOLD:
            result.add_alert(PharmacyRule(
                "LOW_STOCK",
                f"Warning: {product_name} is low on stock ({max_stock} remaining)",
                RuleSeverity.WARNING,
            ))

    def _check_quantity_limits(self, result: PharmacyRuleResult,
                               product_name: str, quantity: int):
        if quantity < self.MIN_BOX_SIZE:
            result.add_alert(PharmacyRule(
                "MIN_QTY",
                f"{product_name}: minimum quantity is {self.MIN_BOX_SIZE}",
                RuleSeverity.WARNING,
            ))
        if quantity > self.MAX_QTY_PER_PRODUCT:
            result.add_alert(PharmacyRule(
                "MAX_QTY",
                f"{product_name}: maximum {self.MAX_QTY_PER_PRODUCT} units per transaction",
                RuleSeverity.WARNING,
            ))

    def _check_prescription(self, result: PharmacyRuleResult,
                            product_name: str, requires_prescription: bool):
        if requires_prescription:
            result.add_alert(PharmacyRule(
                "PRESCRIPTION_REQUIRED",
                f"Prescription required for {product_name} — pharmacist must approve",
                RuleSeverity.WARNING,
            ))

    def _check_controlled(self, result: PharmacyRuleResult,
                          product_name: str, is_controlled: bool):
        if is_controlled:
            result.add_alert(PharmacyRule(
                "CONTROLLED_SUBSTANCE",
                f"Controlled substance: {product_name} — pharmacist approval required",
                RuleSeverity.WARNING,
            ))

    def _check_cold_chain(self, result: PharmacyRuleResult,
                          product_name: str, is_cold_chain: bool):
        if is_cold_chain:
            result.add_alert(PharmacyRule(
                "COLD_CHAIN",
                f"Cold-chain medicine: {product_name} — verify storage before dispensing",
                RuleSeverity.WARNING,
            ))

    def _check_duplicate_medicine(self, result: PharmacyRuleResult,
                                  product_name: str, generic_name: str,
                                  existing_products: set, existing_generics: set):
        if product_name in existing_products:
            result.add_alert(PharmacyRule(
                "DUPLICATE_PRODUCT",
                f"Duplicate: {product_name} already in cart",
                RuleSeverity.INFO,
            ))
        if generic_name and generic_name in existing_generics:
            result.add_alert(PharmacyRule(
                "DUPLICATE_GENERIC",
                f"Therapeutic duplicate: {generic_name} already dispensed "
                f"(via {product_name}) — verify with pharmacist",
                RuleSeverity.WARNING,
            ))

    # ── Return-Specific Compliance Rules ──

    def validate_return(self, return_items: List[Dict]) -> PharmacyRuleResult:
        """Validate return items against pharmacy compliance rules."""
        result = PharmacyRuleResult()

        for item in return_items:
            product_name = item.get("product_name", "")
            condition = item.get("condition", "GOOD")
            is_controlled = item.get("is_controlled", False)
            requires_prescription = item.get("requires_prescription", False)
            is_cold_chain = item.get("is_cold_chain", False)
            expiry_str = item.get("expiry_date", "")

            if is_controlled and condition == "GOOD":
                result.add_alert(PharmacyRule(
                    "CONTROLLED_RETURN",
                    f"Controlled substance return: {product_name} — pharmacist must verify "
                    f"quantity and condition before restocking",
                    RuleSeverity.WARNING,
                ))

            if condition == "EXPIRED":
                result.add_alert(PharmacyRule(
                    "EXPIRED_RETURN",
                    f"{product_name} is expired — route to quarantine, NOT restock",
                    RuleSeverity.WARNING,
                ))

            if condition == "DAMAGED" and is_cold_chain:
                result.add_alert(PharmacyRule(
                    "COLD_CHAIN_DAMAGED",
                    f"Cold-chain product {product_name} returned damaged — dispose per biohazard protocol",
                    RuleSeverity.BLOCKER, is_blocking=True,
                ))

            if is_cold_chain and condition == "GOOD":
                result.add_alert(PharmacyRule(
                    "COLD_CHAIN_RETURN",
                    f"Cold-chain product {product_name} — verify temperature log before restocking",
                    RuleSeverity.WARNING,
                ))

            if requires_prescription:
                result.add_alert(PharmacyRule(
                    "PRESCRIPTION_RETURN",
                    f"Prescription product {product_name} — verify original prescription on file",
                    RuleSeverity.WARNING,
                ))

        return result

    @staticmethod
    def validate_opened_package(item: Dict) -> Optional[PharmacyRule]:
        """Check if a returned item's package was opened (pharmacy policy)."""
        package_opened = item.get("package_opened", False)
        product_name = item.get("product_name", "")
        if package_opened:
            return PharmacyRule(
                "OPENED_PACKAGE",
                f"{product_name}: opened package cannot be restocked — mark as damaged",
                RuleSeverity.WARNING,
            )
        return None
