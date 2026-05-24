from typing import Dict, Any, Optional
from django.db import transaction
from core.drift_prevention.comparator import DriftComparator
from core.drift_prevention.classifier import DriftClassifier
from core.drift_prevention.registry import DriftRegistry


class EquilibriumChecker:
    """Real-time equilibrium check after Gateway execution.

    Verifies structural and financial equality between what JournalEngine
    would have produced and what JournalGateway actually produced.
    """

    @staticmethod
    def verify(
        module: str,
        operation: str,
        reference: str,
        engine_result: Optional[Dict[str, Any]],
        gateway_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        comparison = DriftComparator.compare_results(
            engine_result=engine_result or {},
            gateway_result=gateway_result,
            module=module,
            operation=operation,
        )

        class_label, financial_impact, reasons = DriftClassifier.classify(
            comparison=comparison,
            had_exception=False,
        )

        is_equilibrium = class_label == 'A'

        return {
            'in_equilibrium': is_equilibrium,
            'classification': class_label,
            'financial_impact': financial_impact,
            'differences': comparison.get('differences', []),
            'total_differences': comparison.get('total_differences', 0),
            'reasons': reasons,
        }

    @staticmethod
    def is_stable(check_result: Dict[str, Any]) -> bool:
        return check_result.get('in_equilibrium', False) and check_result.get('total_differences', 0) == 0
