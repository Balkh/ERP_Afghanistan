import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from core.models.drift_prevention import DriftRecord, ModuleDriftState
from core.drift_prevention.comparator import DriftComparator
from core.drift_prevention.classifier import DriftClassifier

logger = logging.getLogger('erp.drift_prevention')


class DriftRegistry:
    """Central registry for all drift detection, classification, and recording.

    This is the single point through which all shadow comparison results flow.
    It performs the comparison, classifies the result, stores it, and updates
    the module-level drift state.

    OBSERVER ONLY — never modifies financial state.
    """

    @staticmethod
    def record(
        module: str,
        operation: str,
        reference: str,
        engine_result: Optional[Dict[str, Any]],
        gateway_result: Optional[Dict[str, Any]],
        had_exception: bool = False,
    ) -> DriftRecord:
        """Record and classify a shadow comparison.

        Args:
            module: Module name (expenses, returns, payments, purchases, sales)
            operation: Operation type (create_entry, reverse_entry, post_entry)
            reference: Document reference number
            engine_result: Result dict from JournalEngine call
            gateway_result: Result dict from JournalGateway call (None if not executed)
            had_exception: True if the shadow call raised an exception

        Returns:
            The created DriftRecord instance
        """
        comparison = DriftComparator.compare_results(
            engine_result=engine_result or {},
            gateway_result=gateway_result,
            module=module,
            operation=operation,
        )

        class_label, financial_impact, reasons = DriftClassifier.classify(
            comparison=comparison,
            had_exception=had_exception,
        )

        engine_entry_id = ''
        gateway_entry_id = ''

        if engine_result and engine_result.get('success'):
            engine_entry_id = str(engine_result.get('entry_id', ''))

        if gateway_result and gateway_result.get('success'):
            gateway_entry_id = str(gateway_result.get('entry_id', ''))

        record = DriftRecord.objects.create(
            module=module,
            operation=operation,
            reference=reference,
            classification=class_label,
            financial_impact=financial_impact,
            engine_entry_id=engine_entry_id,
            gateway_entry_id=gateway_entry_id,
            mismatch_detail={
                'comparison': comparison,
                'reasons': reasons,
                'had_exception': had_exception,
            },
            engine_success=engine_result.get('success') if engine_result else None,
            gateway_success=gateway_result.get('success') if gateway_result else None,
        )

        try:
            DriftRegistry._update_module_state(module, class_label, financial_impact)
        except Exception as e:
            logger.error(f'[DRIFT_REGISTRY] Failed to update module state for {module}: {e}')

        log_level = logging.WARNING if class_label in ('B', 'C', 'D') else logging.INFO
        logger.log(
            log_level,
            f'[DRIFT_REGISTRY] {module}.{operation} [{class_label}] '
            f'impact={financial_impact}, ref={reference}, '
            f'reasons={reasons[:3]}'
        )

        return record

    @staticmethod
    def _update_module_state(
        module: str,
        class_label: str,
        financial_impact: str,
    ):
        state, created = ModuleDriftState.objects.get_or_create(
            module=module,
            defaults={
                'latest_classification': class_label,
                'total_comparisons': 1,
                'class_c_count': 1 if class_label == 'C' else 0,
                'class_d_count': 1 if class_label == 'D' else 0,
                'is_blocked': DriftClassifier.requires_blocking(class_label, financial_impact),
                'block_reason': f'Auto-blocked due to {class_label} drift ({financial_impact} impact)'
                if DriftClassifier.requires_blocking(class_label, financial_impact)
                else '',
                'last_drift_at': timezone.now() if class_label in ('C', 'D') else None,
            },
        )

        if not created:
            state.total_comparisons += 1
            if class_label == 'C':
                state.class_c_count += 1
            if class_label == 'D':
                state.class_d_count += 1

            if DriftClassifier.merge_classifications([state.latest_classification, class_label]) != state.latest_classification:
                state.latest_classification = DriftClassifier.merge_classifications(
                    [state.latest_classification, class_label]
                )

            if DriftClassifier.requires_blocking(class_label, financial_impact) and not state.is_blocked:
                state.is_blocked = True
                state.block_reason = (
                    f'Auto-blocked due to {class_label} drift ({financial_impact} impact). '
                    f'Total Class C: {state.class_c_count}, Class D: {state.class_d_count}'
                )

            if class_label in ('C', 'D'):
                state.last_drift_at = timezone.now()

            state.save()

    @staticmethod
    def get_module_state(module: str) -> Optional[ModuleDriftState]:
        """Get current drift state for a module."""
        try:
            return ModuleDriftState.objects.get(module=module)
        except ModuleDriftState.DoesNotExist:
            return None

    @staticmethod
    def get_all_states() -> list:
        """Get drift states for all tracked modules."""
        return list(ModuleDriftState.objects.all().order_by('module'))

    @staticmethod
    def get_recent_records(module: Optional[str] = None, limit: int = 100) -> list:
        """Get recent drift records, optionally filtered by module."""
        qs = DriftRecord.objects.all()
        if module:
            qs = qs.filter(module=module)
        return list(qs.order_by('-created_at')[:limit])

    @staticmethod
    def get_class_c_records(module: Optional[str] = None) -> list:
        """Get all Class C (Critical) drift records."""
        qs = DriftRecord.objects.filter(classification='C')
        if module:
            qs = qs.filter(module=module)
        return list(qs.order_by('-created_at'))

    @staticmethod
    def is_module_blocked(module: str) -> bool:
        """Check if a module is blocked from Phase 3 migration."""
        state = DriftRegistry.get_module_state(module)
        return state.is_blocked if state else False
