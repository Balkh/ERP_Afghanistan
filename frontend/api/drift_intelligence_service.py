"""
Drift Intelligence Service - Predictive System Integrity Analysis.
Tracks historical integrity snapshots to detect gradual system decay (Drift).
"""

import time
from datetime import datetime
from typing import List, Dict, Any

class DriftIntelligenceService:
    """
    Analyzes historical integrity results to predict systemic issues.
    Stores snapshots locally in memory for drift calculation.
    """
    
    def __init__(self):
        self.snapshots: List[Dict[str, Any]] = []
        self.max_snapshots = 50
        self.modules = ["Accounting", "Inventory", "Sales", "Workflows", "Control Center"]

    def add_snapshot(self, integrity_results: List[Dict[str, Any]]):
        """Record a new integrity scan result for trend analysis."""
        snapshot = {
            "timestamp": datetime.now(),
            "results": integrity_results,
            "metrics": self._calculate_snapshot_metrics(integrity_results)
        }
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)

    def _calculate_snapshot_metrics(self, results):
        """Extract key metrics from integrity results."""
        metrics = {m: {"failures": 0, "warnings": 0} for m in self.modules}
        for res in results:
            for mod in res.get('modules', []):
                if mod in metrics:
                    if res.get('status') == 'FAIL': metrics[mod]["failures"] += 1
                    elif res.get('status') == 'WARNING': metrics[mod]["warnings"] += 1
        return metrics

    def calculate_drift_intelligence(self) -> Dict[str, Any]:
        """Perform predictive analysis on historical snapshots."""
        if len(self.snapshots) < 2:
            return {"status": "insufficient_data"}

        drift_analysis = {
            "overall_drift_score": 0,
            "module_drift": {},
            "warnings": [],
            "risk_heatmap": {}
        }

        total_drift = 0
        for mod in self.modules:
            mod_analysis = self._analyze_module_drift(mod)
            drift_analysis["module_drift"][mod] = mod_analysis
            total_drift += mod_analysis["score"]
            
            # Risk Heatmap Logic (Current State + Trend)
            current_risk = "LOW"
            if mod_analysis["score"] > 70: current_risk = "CRITICAL"
            elif mod_analysis["score"] > 40: current_risk = "HIGH"
            elif mod_analysis["score"] > 20: current_risk = "MEDIUM"
            drift_analysis["risk_heatmap"][mod] = current_risk

            # Early Warnings
            if mod_analysis["trend"] == "UP" and mod_analysis["score"] > 30:
                drift_analysis["warnings"].append(f"Accelerating drift detected in {mod} module.")

        drift_analysis["overall_drift_score"] = int(total_drift / len(self.modules))
        return drift_analysis

    def _analyze_module_drift(self, module: str) -> Dict[str, Any]:
        """Analyze drift for a specific module across snapshots."""
        recent = self.snapshots[-1]["metrics"][module]
        prev = self.snapshots[-2]["metrics"][module]
        
        # Base Score (0-100)
        score = (recent["failures"] * 20) + (recent["warnings"] * 5)
        score = min(score, 100)
        
        # Trend Direction
        trend = "STABLE"
        recent_total = recent["failures"] + recent["warnings"]
        prev_total = prev["failures"] + prev["warnings"]
        
        if recent_total > prev_total: trend = "UP"
        elif recent_total < prev_total: trend = "DOWN"
        
        # Pattern detection (e.g. "Increasing Accounting Lag")
        pattern = "Stable"
        if trend == "UP": pattern = f"Growing inconsistency in {module}"
        elif trend == "DOWN": pattern = f"Integrity improving in {module}"
        
        return {
            "score": score,
            "trend": trend,
            "pattern": pattern,
            "failures": recent["failures"],
            "warnings": recent["warnings"]
        }

    def get_trend_data(self, module: str) -> List[float]:
        """Extract scores for sparkline visualization."""
        trend = []
        for snap in self.snapshots:
            m = snap["metrics"][module]
            s = (m["failures"] * 20) + (m["warnings"] * 5)
            trend.append(float(min(s, 100)))
        return trend
