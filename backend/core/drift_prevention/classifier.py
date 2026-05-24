from typing import Dict, List, Any, Tuple


class DriftClassifier:
    """Classifies shadow comparison results into A/B/C/D categories.

    Classification Rules:
        A — Match: No differences or only non-financial formatting differences
        B — Minor Deviation: Line descriptions, non-financial metadata
        C — Financial Drift (CRITICAL): Balance mismatches, missing entries, wrong accounts
        D — System Failure: Shadow execution crashed or produced inconsistent state
    """

    CRITICAL_SEVERITIES = {'CRITICAL', 'HIGH'}

    @staticmethod
    def classify(
        comparison: Dict[str, Any],
        had_exception: bool = False,
    ) -> Tuple[str, str, List[str]]:
        """Classify comparison results.

        Args:
            comparison: Output from DriftComparator.compare_results()
            had_exception: True if the shadow call itself raised an exception

        Returns:
            Tuple of (class_label, financial_impact, reasons)
            class_label: 'A', 'B', 'C', or 'D'
            financial_impact: 'NONE', 'LOW', 'HIGH', or 'CRITICAL'
            reasons: List of human-readable reasons for the classification
        """
        reasons = []

        if had_exception:
            reasons.append('Shadow execution raised an exception — system failure detected')
            return 'D', 'CRITICAL', reasons

        differences = comparison.get('differences', [])
        if not differences:
            reasons.append('All fields match — no drift detected')
            return 'A', 'NONE', reasons

        engine_entries = comparison.get('engine_entries', [])
        gateway_entries = comparison.get('gateway_entries', [])

        if not engine_entries and not gateway_entries:
            reasons.append('Both engine and gateway produced no entries — no comparison possible')
            return 'A', 'NONE', reasons

        if not engine_entries and gateway_entries:
            reasons.append('JournalEngine produced no entry but JournalGateway did — possible engine failure')
            return 'C', 'CRITICAL', reasons

        if engine_entries and not gateway_entries:
            reasons.append('JournalGateway produced no entry but JournalEngine did — gateway failure')
            return 'D', 'HIGH', reasons

        has_critical = any(
            d.get('severity') in DriftClassifier.CRITICAL_SEVERITIES
            for d in differences
        )
        has_minor = any(
            d.get('severity') == 'LOW'
            for d in differences
        )

        critical_impact = DriftClassifier._assess_critical_impact(differences)

        if has_critical:
            for d in differences:
                if d.get('severity') in DriftClassifier.CRITICAL_SEVERITIES:
                    reasons.append(
                        f"CRITICAL drift at {d.get('field', 'unknown')}: "
                        f"engine={d.get('engine', '?')}, gateway={d.get('gateway', '?')}"
                    )
            return 'C', critical_impact, reasons

        if has_minor:
            for d in differences:
                reasons.append(
                    f"Minor drift at {d.get('field', 'unknown')}: "
                    f"engine={d.get('engine', '?')}, gateway={d.get('gateway', '?')}"
                )
            return 'B', 'LOW', reasons

        reasons.append('Unclassified differences detected')
        return 'B', 'LOW', reasons

    @staticmethod
    def _assess_critical_impact(differences: List[Dict[str, Any]]) -> str:
        severity_levels = [d.get('severity', 'LOW') for d in differences]
        if 'CRITICAL' in severity_levels:
            critical_count = severity_levels.count('CRITICAL')
            if critical_count >= 3:
                return 'CRITICAL'
            return 'HIGH'
        if 'HIGH' in severity_levels:
            return 'HIGH'
        return 'LOW'

    @staticmethod
    def requires_blocking(class_label: str, financial_impact: str) -> bool:
        """Determine if this classification should block a module from Phase 3."""
        return class_label == 'C' or (class_label == 'D' and financial_impact == 'CRITICAL')

    @staticmethod
    def merge_classifications(classifications: List[str]) -> str:
        """Merge multiple classifications into the worst case."""
        priority = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        worst = 'A'
        for c in classifications:
            if priority.get(c, 0) > priority.get(worst, 0):
                worst = c
        return worst
