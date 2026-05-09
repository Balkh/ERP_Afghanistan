#!/usr/bin/env python3
"""
PHASED CI ENFORCEMENT ROLLOUT STRATEGY
======================================
Safe transition from monitoring mode to strict blocking.

Phase 0: Current State (Monitoring Only)
Phase 1: Soft Warning (Non-blocking reports)
Phase 2: Advisory Blocking (Warnings + CI visibility)
Phase 3: Gradual Enforcement (Percentage-based blocking)
Phase 4: Full Enforcement (Strict blocking)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
FRONTEND_DIR = Path(__file__).parent.parent
CONFIG_FILE = FRONTEND_DIR / "scripts" / "ci_rollout_config.json"
VIOLATIONS_LOG = FRONTEND_DIR / "scripts" / "violations_log.json"

# =====================================================
# PHASE DEFINITIONS
# =====================================================

PHASES = {
    "PHASE_0_MONITORING": {
        "name": "Monitoring Only",
        "description": "Current state - violations detected but not blocked",
        "blocking": False,
        "severity": "INFO",
        "exit_criteria": "Baseline established",
    },
    "PHASE_1_WARNING": {
        "name": "Soft Warning",
        "description": "Non-blocking but visible in CI logs",
        "blocking": False,
        "severity": "WARNING",
        "exit_criteria": "80% compliance, 2 weeks no regression",
    },
    "PHASE_2_ADVISORY": {
        "name": "Advisory Blocking",
        "description": "New violations blocked, existing violations tracked",
        "blocking": True,
        "new_only": True,
        "severity": "ERROR",
        "exit_criteria": "90% compliance, 4 weeks stability",
    },
    "PHASE_3_GRADUAL": {
        "name": "Gradual Enforcement",
        "description": "Progressive blocking based on file priority",
        "blocking": True,
        "threshold": 0.85,
        "severity": "ERROR",
        "exit_criteria": "95% compliance, stable CI",
    },
    "PHASE_4_STRICT": {
        "name": "Full Enforcement",
        "description": "Strict blocking on all violations",
        "blocking": True,
        "threshold": 1.0,
        "severity": "ERROR",
        "exit_criteria": "100% compliance target",
    },
}

# =====================================================
# FILE PRIORITY TIERS
# =====================================================

PRIORITY_TIERS = {
    "TIER_1_CRITICAL": {
        "files": ["main_window.py", "sidebar.py", "dashboard.py"],
        "description": "Core navigation and layout - must be tokenized",
        "blocking_percentage": 0.0,  # Start with 0% blocking
    },
    "TIER_2_HIGH": {
        "files": [
            "user_management_screen.py",
            "accounting_dashboard.py",
            "journal_entry_screen.py",
            "control_center_screen.py",
        ],
        "description": "High-visibility business screens",
        "blocking_percentage": 0.0,
    },
    "TIER_3_MEDIUM": {
        "files": [
            "buttons.py", "forms.py", "dialogs.py", "tables.py",
            "payroll_screen.py", "employee_screen.py", "attendance_screen.py",
        ],
        "description": "Shared components and HR screens",
        "blocking_percentage": 0.0,
    },
    "TIER_4_LOW": {
        "files": [],  # All other files
        "description": "Lower priority screens",
        "blocking_percentage": 0.0,
    },
}


class CIRolloutManager:
    """Manages phased CI enforcement rollout."""

    def __init__(self):
        self.config = self._load_config()
        self.current_phase = self.config.get("current_phase", "PHASE_0_MONITORING")
        self.violations_log = self._load_violations_log()
        
    def _load_config(self) -> dict:
        """Load rollout configuration."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {
            "current_phase": "PHASE_0_MONITORING",
            "phase_history": [],
            "rollout_start_date": datetime.now().isoformat(),
            "exit_criteria_met": {},
            "file_tiers": PRIORITY_TIERS,
        }
    
    def _save_config(self):
        """Save rollout configuration."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2, default=str)
    
    def _load_violations_log(self) -> dict:
        """Load violations tracking log."""
        if VIOLATIONS_LOG.exists():
            with open(VIOLATIONS_LOG, 'r') as f:
                return json.load(f)
        return {
            "entries": [],
            "baseline": {},
            "regression_count": 0,
        }
    
    def _save_violations_log(self):
        """Save violations tracking log."""
        with open(VIOLATIONS_LOG, 'w') as f:
            json.dump(self.violations_log, f, indent=2, default=str)
    
    def get_phase_info(self) -> dict:
        """Get current phase information."""
        return PHASES.get(self.current_phase, PHASES["PHASE_0_MONITORING"])
    
    def should_block(self, file_path: str, violation_count: int) -> tuple[bool, str]:
        """Determine if a file should be blocked based on current phase."""
        phase_info = self.get_phase_info()
        
        # Phase 0-1: No blocking
        if not phase_info.get("blocking", False):
            return False, f"Phase {self.current_phase}: Monitoring only"
        
        # Phase 2: Block only new violations
        if phase_info.get("new_only", False):
            baseline = self.violations_log.get("baseline", {})
            file_baseline = baseline.get(file_path, 0)
            if violation_count > file_baseline:
                return True, f"New violations detected: {violation_count} > baseline {file_baseline}"
            return False, "No regression from baseline"
        
        # Phase 3: Percentage-based blocking
        threshold = phase_info.get("threshold", 1.0)
        tier = self._get_file_tier(file_path)
        tier_blocking = tier.get("blocking_percentage", 0.0) if tier else 0.0
        
        effective_threshold = threshold * tier_blocking
        if effective_threshold > 0 and violation_count > 0:
            # Simple heuristic: block if violations exceed threshold
            return True, f"Phase 3 threshold exceeded: {violation_count} violations"
        
        return False, "Within threshold"
    
    def _get_file_tier(self, file_path: str) -> dict:
        """Get priority tier for a file."""
        filename = os.path.basename(file_path)
        for tier_name, tier_info in PRIORITY_TIERS.items():
            if filename in tier_info.get("files", []):
                return tier_info
        return PRIORITY_TIERS["TIER_4_LOW"]
    
    def record_violations(self, file_path: str, violation_count: int):
        """Record violations for tracking and baseline."""
        if not self.violations_log.get("baseline"):
            # Initialize baseline on first run
            self.violations_log["baseline"] = {}
        
        baseline = self.violations_log.get("baseline", {})
        if file_path not in baseline:
            baseline[file_path] = violation_count
        
        self.violations_log["entries"].append({
            "timestamp": datetime.now().isoformat(),
            "file": file_path,
            "count": violation_count,
            "phase": self.current_phase,
        })
        self._save_violations_log()
    
    def advance_phase(self, new_phase: str) -> bool:
        """Advance to next phase with validation."""
        if new_phase not in PHASES:
            print(f"Error: Unknown phase {new_phase}")
            return False
        
        # Validate exit criteria for current phase
        current_phase_info = PHASES[self.current_phase]
        exit_criteria = current_phase_info.get("exit_criteria", "")
        
        # For now, allow manual phase advancement
        old_phase = self.current_phase
        self.current_phase = new_phase
        self.config["current_phase"] = new_phase
        self.config["phase_history"].append({
            "from": old_phase,
            "to": new_phase,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_config()
        
        print(f"Phase advanced: {old_phase} -> {new_phase}")
        print(f"Exit criteria was: {exit_criteria}")
        return True
    
    def get_status_report(self) -> str:
        """Generate status report."""
        phase_info = self.get_phase_info()
        
        report = f"""
================================================================================
CI ENFORCEMENT ROLLOUT STATUS REPORT
================================================================================

Current Phase: {self.current_phase}
Phase Name: {phase_info['name']}
Description: {phase_info['description']}

Blocking Enabled: {phase_info.get('blocking', False)}
Severity: {phase_info.get('severity', 'N/A')}

Exit Criteria: {phase_info.get('exit_criteria', 'N/A')}

Rollout Start: {self.config.get('rollout_start_date', 'Unknown')}
Phase History: {len(self.config.get('phase_history', []))} transitions

================================================================================
"""
        return report


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="CI Enforcement Rollout Manager")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--phase", type=str, help="Advance to specified phase")
    parser.add_argument("--check", type=str, help="Check if file should be blocked")
    parser.add_argument("--record", type=str, help="Record violations for file")
    
    args = parser.parse_args()
    
    manager = CIRolloutManager()
    
    if args.status:
        print(manager.get_status_report())
    elif args.phase:
        manager.advance_phase(args.phase)
    elif args.check:
        should_block, reason = manager.should_block(args.check, 10)
        print(f"File: {args.check}")
        print(f"Should Block: {should_block}")
        print(f"Reason: {reason}")
    elif args.record:
        manager.record_violations(args.record, 5)
        print(f"Recorded violations for {args.record}")
    else:
        print(manager.get_status_report())


if __name__ == "__main__":
    main()