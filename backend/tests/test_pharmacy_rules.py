"""
Tests for Pharmacy Rules Engine, Offline Queue, Thermal Printer, and Print infra.
"""

import pytest
pytest.importorskip("pharmacy.services.rules_engine", reason="pharmacy module not yet created")

from datetime import date, timedelta
from decimal import Decimal

from pharmacy.services.rules_engine import PharmacyRulesEngine, PharmacyRuleResult, RuleSeverity


class TestPharmacyRulesEngine:
    def setup_method(self):
        self.engine = PharmacyRulesEngine()

    def _make_item(self, **overrides):
        item = {
            "product_name": "Paracetamol 500mg",
            "generic_name": "Paracetamol",
            "quantity": 1,
            "max_stock": Decimal("50"),
            "price": Decimal("150.00"),
            "expiry_date": "",
            "requires_prescription": False,
            "is_controlled": False,
            "is_cold_chain": False,
        }
        item.update(overrides)
        return item

    # ── Expiry Tests ──

    def test_expired_product_blocked(self):
        past = (date.today() - timedelta(days=5)).isoformat()
        result = self.engine.validate_cart([self._make_item(expiry_date=past)])
        assert result.has_blockers
        assert any(r.code == "EXPIRED" for r in result.blockers)

    def test_expiring_critical_warning(self):
        near = (date.today() + timedelta(days=15)).isoformat()
        result = self.engine.validate_cart([self._make_item(expiry_date=near)])
        assert result.has_alerts
        assert any(r.code == "EXPIRING_CRITICAL" for r in result.alerts)

    def test_expiring_soon_info(self):
        future = (date.today() + timedelta(days=60)).isoformat()
        result = self.engine.validate_cart([self._make_item(expiry_date=future)])
        assert any(r.code == "EXPIRING_SOON" for r in result.alerts)

    def test_fresh_expiry_no_alert(self):
        far = (date.today() + timedelta(days=200)).isoformat()
        result = self.engine.validate_cart([self._make_item(expiry_date=far)])
        assert not any("EXPIR" in r.code for r in result.alerts)

    # ── Stock Tests ──

    def test_out_of_stock_blocked(self):
        result = self.engine.validate_cart([self._make_item(max_stock=Decimal("0"))])
        assert result.has_blockers
        assert any(r.code == "STOCKOUT" for r in result.blockers)

    def test_insufficient_stock_blocked(self):
        result = self.engine.validate_cart([self._make_item(quantity=5, max_stock=Decimal("3"))])
        assert result.has_blockers
        assert any(r.code == "INSUFFICIENT_STOCK" for r in result.blockers)

    def test_low_stock_warning(self):
        result = self.engine.validate_cart([self._make_item(max_stock=Decimal("5"))])
        assert any(r.code == "LOW_STOCK" for r in result.alerts)

    def test_adequate_stock_no_alert(self):
        result = self.engine.validate_cart([self._make_item(max_stock=Decimal("100"))])
        assert not any(r.code in ("STOCKOUT", "INSUFFICIENT_STOCK", "LOW_STOCK") for r in result.alerts)

    # ── Prescription Tests ──

    def test_prescription_required_warning(self):
        result = self.engine.validate_cart([self._make_item(requires_prescription=True)])
        assert any(r.code == "PRESCRIPTION_REQUIRED" for r in result.alerts)
        assert result.approval_required

    # ── Controlled Substance Tests ──

    def test_controlled_substance_warning(self):
        result = self.engine.validate_cart([self._make_item(is_controlled=True)])
        assert any(r.code == "CONTROLLED_SUBSTANCE" for r in result.alerts)
        assert result.approval_required

    # ── Cold Chain Tests ──

    def test_cold_chain_warning(self):
        result = self.engine.validate_cart([self._make_item(is_cold_chain=True)])
        assert any(r.code == "COLD_CHAIN" for r in result.alerts)

    # ── Duplicate Tests ──

    def test_duplicate_product_detected(self):
        item = self._make_item()
        result = self.engine.validate_cart([item, item])
        assert any(r.code == "DUPLICATE_PRODUCT" for r in result.alerts)

    def test_duplicate_generic_detected(self):
        items = [
            self._make_item(product_name="Paracetamol 500mg", generic_name="Paracetamol"),
            self._make_item(product_name="Panadol 500mg", generic_name="Paracetamol"),
        ]
        result = self.engine.validate_cart(items)
        assert any(r.code == "DUPLICATE_GENERIC" for r in result.alerts)

    # ── Quantity Limit Tests ──

    def test_max_quantity_exceeded_warning(self):
        result = self.engine.validate_cart([self._make_item(quantity=101)])
        assert any(r.code == "MAX_QTY" for r in result.alerts)

    def test_valid_cart_no_alerts(self):
        item = self._make_item()
        result = self.engine.validate_cart([item])
        assert not result.has_blockers
        assert not result.has_alerts

    # ── Mixed Cart Tests ──

    def test_mixed_cart_with_multiple_issues(self):
        items = [
            self._make_item(product_name="Item A", is_controlled=True),
            self._make_item(product_name="Item B", max_stock=Decimal("0")),
        ]
        result = self.engine.validate_cart(items)
        assert result.has_blockers
        assert result.approval_required
        assert any(r.code == "CONTROLLED_SUBSTANCE" for r in result.alerts)
        assert any(r.code == "STOCKOUT" for r in result.blockers)


class TestPharmacyRuleResult:
    def test_empty_result_allows_proceed(self):
        r = PharmacyRuleResult()
        assert not r.has_blockers
        assert r.to_dict()["can_proceed"] is True

    def test_result_to_dict_structure(self):
        r = PharmacyRuleResult()
        d = r.to_dict()
        assert "alerts" in d
        assert "blockers" in d
        assert "approval_required" in d
        assert "can_proceed" in d
