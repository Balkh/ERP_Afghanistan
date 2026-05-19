"""
Recovery Certification Report generator for backup/restore disaster recovery validation.

Generates a structured recovery certification report that combines validation results
from AccountingRecoveryValidator and InventoryRecoveryValidator, calculates a
recovery confidence level (0-100), and determines certification status.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.backup.certification')


class RecoveryCertificationReport:
    """Generates a structured recovery certification report.

    Accepts validation results from AccountingRecoveryValidator and
    InventoryRecoveryValidator, calculates a confidence score, and
    determines certification status (CERTIFIED / CONDITIONAL / FAILED).

    Confidence scoring:
        - All accounting checks passed: +30 points
        - All inventory checks passed: +30 points
        - Backup checksum valid: +15 points
        - No orphaned records: +15 points
        - Rollback tested: +10 points

    Status logic:
        - CERTIFIED: confidence >= 90
        - CONDITIONAL: confidence >= 60
        - FAILED: confidence < 60
    """

    def __init__(
        self,
        accounting_results: Optional[Dict[str, Any]] = None,
        inventory_results: Optional[Dict[str, Any]] = None,
        restore_duration_seconds: float = 0.0,
        validation_duration_seconds: float = 0.0,
        backup_checksum_valid: bool = False,
        has_orphaned_records: bool = False,
        rollback_tested: bool = False,
        rollback_result: Optional[Dict[str, Any]] = None,
        corruption_findings: Optional[List[Dict[str, Any]]] = None,
    ):
        self.accounting_results = accounting_results or {}
        self.inventory_results = inventory_results or {}
        self.restore_duration_seconds = restore_duration_seconds
        self.validation_duration_seconds = validation_duration_seconds
        self.backup_checksum_valid = backup_checksum_valid
        self.has_orphaned_records = has_orphaned_records
        self.rollback_tested = rollback_tested
        self.rollback_result = rollback_result or {}
        self.corruption_findings = corruption_findings or []

    def calculate_confidence(self) -> int:
        """Calculate recovery confidence level (0-100).

        Scoring breakdown:
            +30: All accounting checks passed
            +30: All inventory checks passed
            +15: Backup checksum valid
            +15: No orphaned records
            +10: Rollback tested
        """
        score = 0

        if self._all_accounting_checks_passed():
            score += 30

        if self._all_inventory_checks_passed():
            score += 30

        if self.backup_checksum_valid:
            score += 15

        if not self.has_orphaned_records:
            score += 15

        if self.rollback_tested:
            score += 10

        return min(score, 100)

    def determine_status(self, confidence: int) -> str:
        """Determine certification status based on confidence level."""
        if confidence >= 90:
            return 'CERTIFIED'
        elif confidence >= 60:
            return 'CONDITIONAL'
        else:
            return 'FAILED'

    def generate(self) -> Dict[str, Any]:
        """Generate the full recovery certification report.

        Returns:
            dict with certification_id, timestamp, status, confidence_level,
            restore/validation durations, validation results, corruption
            findings, rollback results, failed scenarios, and recommendations.
        """
        confidence = self.calculate_confidence()
        status = self.determine_status(confidence)

        failed_scenarios = self._collect_failed_scenarios()
        recommendations = self._generate_recommendations(status, failed_scenarios)

        report = {
            'certification_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': status,
            'confidence_level': confidence,
            'restore_duration_seconds': self.restore_duration_seconds,
            'validation_duration_seconds': self.validation_duration_seconds,
            'accounting_validation': self.accounting_results,
            'inventory_validation': self.inventory_results,
            'corruption_findings': self.corruption_findings,
            'rollback_test_result': self.rollback_result,
            'failed_scenarios': failed_scenarios,
            'recommendations': recommendations,
        }

        logger.info(
            f"Recovery certification generated: status={status}, "
            f"confidence={confidence}, id={report['certification_id']}"
        )

        return report

    def _all_accounting_checks_passed(self) -> bool:
        """Check if all accounting validation checks passed."""
        if not self.accounting_results:
            return False
        return self.accounting_results.get('valid', False)

    def _all_inventory_checks_passed(self) -> bool:
        """Check if all inventory validation checks passed."""
        if not self.inventory_results:
            return False
        return self.inventory_results.get('valid', False)

    def _collect_failed_scenarios(self) -> List[Dict[str, Any]]:
        """Collect all failed validation checks into a list."""
        failed = []

        if self.accounting_results:
            for check in self.accounting_results.get('checks', []):
                if not check.get('passed', True):
                    failed.append({
                        'domain': 'accounting',
                        'check': check.get('name', 'unknown'),
                        'details': check.get('details', ''),
                        'count': check.get('count', 0),
                    })

        if self.inventory_results:
            for check in self.inventory_results.get('checks', []):
                if not check.get('passed', True):
                    failed.append({
                        'domain': 'inventory',
                        'check': check.get('name', 'unknown'),
                        'details': check.get('details', ''),
                        'count': check.get('count', 0),
                    })

        for finding in self.corruption_findings:
            if finding.get('severity') in ('critical', 'error'):
                failed.append({
                    'domain': 'corruption',
                    'check': finding.get('scan_type', 'unknown'),
                    'details': finding.get('message', ''),
                    'count': finding.get('count', 1),
                })

        return failed

    def _generate_recommendations(
        self, status: str, failed_scenarios: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations based on report state."""
        recommendations = []

        if status == 'FAILED':
            recommendations.append(
                'Recovery is not certified. Do not use this restored database '
                'for production operations until all issues are resolved.'
            )

        if not self._all_accounting_checks_passed():
            recommendations.append(
                'Accounting validation failed. Review journal entry balances, '
                'debit/credit equality, and invoice-payment consistency.'
            )

        if not self._all_inventory_checks_passed():
            recommendations.append(
                'Inventory validation failed. Check stock quantity consistency, '
                'batch integrity, and movement chain continuity.'
            )

        if not self.backup_checksum_valid:
            recommendations.append(
                'Backup checksum could not be verified. Ensure the backup file '
                'was not corrupted during transfer or storage.'
            )

        if self.has_orphaned_records:
            recommendations.append(
                'Orphaned records detected. Review foreign key relationships '
                'and clean up dangling references.'
            )

        if not self.rollback_tested:
            recommendations.append(
                'Rollback has not been tested. Perform a rollback test to '
                'verify recovery reversibility before certifying.'
            )

        if self.corruption_findings:
            critical_count = sum(
                1 for f in self.corruption_findings
                if f.get('severity') == 'critical'
            )
            if critical_count > 0:
                recommendations.append(
                    f'Found {critical_count} critical corruption findings. '
                    'Investigate and resolve before production use.'
                )

        if self.rollback_result and not self.rollback_result.get('success', True):
            recommendations.append(
                'Rollback test failed. Verify emergency backup integrity '
                'and rollback procedure before certifying recovery.'
            )

        if not recommendations:
            recommendations.append(
                'All validation checks passed. Recovery is certified for '
                'production use.'
            )

        return recommendations
