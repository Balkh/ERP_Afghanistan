"""
RootCauseEngine — Root cause intelligence orchestrator for Phase 3B.
Read-only analysis of Phase 3A mismatch data.
WHY mismatches happened — NOT how to fix them.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.correlator.event_correlator import (
    EventCorrelator,
)
from simulation.truth_engine.root_cause.classifier.root_cause_classifier import (
    RootCauseClassifier,
)
from simulation.truth_engine.root_cause.analyzer.causal_analyzer import (
    CausalAnalyzer,
)
from simulation.truth_engine.root_cause.patterns.drift_pattern_detector import (
    DriftPatternDetector,
)
from simulation.truth_engine.root_cause.explainer.explanation_engine import (
    RootCauseExplainer,
)
from simulation.truth_engine.root_cause.graph.causal_graph_builder import (
    CausalGraphBuilder,
)
from simulation.truth_engine.root_cause.history.drift_memory import (
    DriftMemoryStore,
)
from simulation.truth_engine.root_cause.models import (
    RootCause, CausalChain, DriftPattern, Explanation, CausalGraph,
)


logger = logging.getLogger('erp.simulation.truth.root_cause.engine')


class RootCauseEngine:
    """
    Orchestrates all root cause analysis components.
    Reads Phase 3A mismatch output. Generates explanations.
    NO mutation of any data. Read-only analysis only.
    """

    def __init__(self):
        self._correlator = EventCorrelator()
        self._classifier = RootCauseClassifier()
        self._analyzer = CausalAnalyzer()
        self._pattern_detector = DriftPatternDetector()
        self._explainer = RootCauseExplainer()
        self._graph_builder = CausalGraphBuilder()
        self._memory = DriftMemoryStore()
        self._current_tick: int = 0

    def analyze_mismatch(
        self,
        mismatch: Dict[str, Any],
        event_history: List[Any],
        workflow_completions: Dict[str, int],
        agent_executions: Dict[str, int],
        tick: int,
    ) -> Dict[str, Any]:
        mismatch_id = mismatch.get('mismatch_id', 'unknown')
        mismatch_type = mismatch.get('mismatch_type', 'unknown')
        mismatch_desc = mismatch.get('description', '')
        affected_module = mismatch.get('affected_module', 'unknown')
        self._current_tick = tick
        chain = self._correlator.correlate(
            mismatch_id=mismatch_id,
            mismatch_type=mismatch_type,
            mismatch_description=mismatch_desc,
            affected_module=affected_module,
            mismatch_tick=tick,
            event_history=event_history,
            workflow_completions=workflow_completions,
            agent_executions=agent_executions,
        )
        root_cause = self._classifier.classify(
            mismatch_id=mismatch_id,
            mismatch_type=mismatch_type,
            mismatch_description=mismatch_desc,
            affected_module=affected_module,
            tick=tick,
            event_count=len(chain.links),
        )
        analysis = self._analyzer.analyze(
            chain=chain,
            root_cause=root_cause,
            agent_executions=agent_executions,
            workflow_completions=workflow_completions,
        )
        explanation = self._explainer.explain(
            mismatch_id=mismatch_id,
            mismatch_type=mismatch_type,
            mismatch_description=mismatch_desc,
            affected_module=affected_module,
            tick=tick,
            root_cause=root_cause,
            causal_chain=chain,
        )
        self._memory.record_drift(tick, mismatch, root_cause)
        return {
            'mismatch_id': mismatch_id,
            'causal_chain': chain.to_dict(),
            'root_cause': root_cause.to_dict(),
            'analysis': analysis,
            'explanation': explanation.to_dict(),
        }

    def detect_patterns(
        self, mismatch_history: List[Dict[str, Any]],
    ) -> List[DriftPattern]:
        return self._pattern_detector.detect(
            mismatch_history, self._current_tick
        )

    def build_causal_graph(
        self,
        scenario_id: str,
        mismatches: List[Dict[str, Any]],
        agent_executions: Dict[str, int],
        workflow_completions: Dict[str, int],
    ) -> CausalGraph:
        all_links = []
        all_causes = []
        for m in mismatches:
            cid = f"chain_{m.get('mismatch_id', 'unknown')}"
            chain = self._correlator.get_chain(cid)
            if chain:
                all_links.extend(chain.links)
            cid2 = f"cause_{m.get('mismatch_id', 'unknown')}"
            cause = self._classifier.get_classification(cid2)
            if cause:
                all_causes.append(cause)
        return self._graph_builder.build(
            graph_id=f"graph_{scenario_id}_{self._current_tick}",
            mismatches=mismatches,
            chains=all_links,
            root_causes=all_causes,
            agent_executions=agent_executions,
            workflow_completions=workflow_completions,
        )

    def record_run_patterns(
        self, run_id: str, patterns: List[DriftPattern],
    ):
        self._memory.record_patterns(run_id, patterns)

    def get_drift_history(
        self, since_tick: int = 0,
    ) -> List[Dict[str, Any]]:
        return self._memory.get_drift_history(since_tick)

    def get_high_risk_workflows(
        self, min_frequency: int = 2,
    ) -> Dict[str, int]:
        return self._memory.get_high_risk_workflows(min_frequency)

    @property
    def correlator(self) -> EventCorrelator:
        return self._correlator

    @property
    def classifier(self) -> RootCauseClassifier:
        return self._classifier

    @property
    def analyzer(self) -> CausalAnalyzer:
        return self._analyzer

    @property
    def pattern_detector(self) -> DriftPatternDetector:
        return self._pattern_detector

    @property
    def explainer(self) -> RootCauseExplainer:
        return self._explainer

    @property
    def graph_builder(self) -> CausalGraphBuilder:
        return self._graph_builder

    @property
    def memory(self) -> DriftMemoryStore:
        return self._memory

    @property
    def explanation_count(self) -> int:
        return self._explainer.explanation_count

    @property
    def pattern_count(self) -> int:
        return self._pattern_detector.pattern_count
