"""Unit tests for format_health_report() pure function.

Extracted from backup_screen.py — pure function, no Qt usage at call time.
Note: importing from backup_screen triggers PySide6 at module level.
"""

from ui.system.backup_screen import format_health_report


class TestFormatHealthReport:
    """Test the format_health_report pure function with various status data shapes."""

    def test_empty_dict(self):
        """Empty status data should produce a report with defaults."""
        result = format_health_report({})
        assert "Backup Status: Unknown" in result
        assert "Total Backups: 0" in result
        assert "Total Size: 0.0 MB" in result
        assert "Last Backup: —" in result
        assert "Warnings:" in result
        assert "Errors:" in result

    def test_full_status_data(self):
        """Complete status data should render all fields correctly."""
        data = {
            "backup_status": "healthy",
            "total_backups": 5,
            "total_size_mb": 128.5,
            "last_backup_time": "2026-06-07T10:00:00",
            "restore_lock_active": True,
            "certification_status": "CERTIFIED",
            "certification_score": 92,
            "email_status": "enabled",
            "email_pending_count": 3,
            "encryption_configured": True,
            "warnings": ["Low disk space"],
            "errors": [],
        }
        result = format_health_report(data)
        assert "Backup Status: Healthy" in result
        assert "Total Backups: 5" in result
        assert "Total Size: 128.5 MB" in result
        assert "Last Backup: 2026-06-07T10:00:00" in result
        assert "Restore Lock: Active" in result
        assert "Certification: CERTIFIED (92/100)" in result
        assert "Email Status: Enabled" in result
        assert "Email Pending: 3" in result
        assert "Encryption: Configured" in result
        assert "  - Low disk space" in result
        assert "  (none)" in result  # errors section

    def test_restore_lock_inactive(self):
        """Inactive restore lock should display correctly."""
        data = {"restore_lock_active": False}
        result = format_health_report(data)
        assert "Restore Lock: Inactive" in result

    def test_encryption_not_set(self):
        """Encryption not configured should display correctly."""
        data = {"encryption_configured": False}
        result = format_health_report(data)
        assert "Encryption: Not Set" in result

    def test_warnings_list(self):
        """All warning sources should be aggregated."""
        data = {
            "warnings": ["w1"],
            "health_warnings": ["w2"],
            "corruption_warnings": ["w3"],
        }
        result = format_health_report(data)
        assert "  - w1" in result
        assert "  - w2" in result
        assert "  - w3" in result

    def test_errors_list(self):
        """All error sources should be aggregated."""
        data = {
            "errors": ["e1"],
            "health_errors": ["e2"],
            "corruption_errors": ["e3"],
        }
        result = format_health_report(data)
        assert "  - e1" in result
        assert "  - e2" in result
        assert "  - e3" in result

    def test_no_warnings_no_errors(self):
        """Empty warnings and errors should show '(none)' placeholders."""
        data = {"warnings": [], "errors": []}
        result = format_health_report(data)
        # Both sections should show (none)
        assert result.count("  (none)") >= 2, "Expected '(none)' in both Warnings and Errors sections"

    def test_zero_total_backups(self):
        """Zero backups should display correctly."""
        data = {"total_backups": 0, "total_size_mb": 0.0}
        result = format_health_report(data)
        assert "Total Backups: 0" in result
        assert "Total Size: 0.0 MB" in result
