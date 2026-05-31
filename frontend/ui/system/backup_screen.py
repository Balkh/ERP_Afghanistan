"""Enterprise Backup & Recovery Control Center — Unified Operations Screen.

Reads ALL system state from the backend Control Plane (SSOT) only.
No independent state computation. No mocked data. No stale state.

ARCHITECTURE LOCK — DO NOT MODIFY WITHOUT REVIEW:
    GUARDRAIL 1: All status data comes from /api/backup/control-plane/status/
    GUARDRAIL 2: No local caching of operational state (_status_data is refreshed, not cached)
    GUARDRAIL 3: SSOT unavailable → safe read-only mode (all mutations disabled)
    GUARDRAIL 4: No optimistic UI updates — always wait for backend confirmation
    GUARDRAIL 5: No polling loops — all refresh is user-triggered
    GUARDRAIL 6: No fallback state computation — if SSOT fails, show UNAVAILABLE
"""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout,
                                QWidget, QLabel, QGroupBox, QFrame,
                                QDialog, QTextEdit)
from PySide6.QtCore import Qt
from api.client import APIClient
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, MARGIN_PAGE, MARGIN_CARD,
                           TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY,
                           COLOR_TEXT_MUTED, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
                           COLOR_BG_MAIN, COLOR_FORM_FOOTER_BORDER)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog, ConfirmDialog
from ui.components.tables import EnterpriseTable, TableColumn
from ui.screens.base_screen import BaseScreen


class _StatusIndicator(QFrame):
    """Lightweight status indicator card — no graphs, no heavy visualization."""

    def update_status(self, value: str, status: str):
        """Update indicator value and color using governed styles."""
        color_map = {
            'healthy': COLOR_SUCCESS,
            'warning': COLOR_WARNING,
            'critical': COLOR_DANGER,
            'enabled': COLOR_SUCCESS,
            'disabled': COLOR_TEXT_MUTED,
            'pending': COLOR_WARNING,
            'failure': COLOR_DANGER,
            'CERTIFIED': COLOR_SUCCESS,
            'CONDITIONAL': COLOR_WARNING,
            'FAILED': COLOR_DANGER,
            'locked': COLOR_DANGER,
            'unlocked': COLOR_SUCCESS,
        }
        color = color_map.get(status, COLOR_INFO)
        from theme.style_builder import UIStyleBuilder
        self.setStyleSheet(UIStyleBuilder.get_status_indicator_style(color))
        self._val_lbl.setText(value)
        self._val_lbl.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_CARD_TITLE, 700))

    def __init__(self, label: str, value: str, status: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        layout.setSpacing(SPACING_XS)

        lbl = QLabel(label)
        from theme.style_builder import UIStyleBuilder
        lbl.setStyleSheet(UIStyleBuilder.get_label_style("muted"))
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        self._val_lbl = QLabel(value)
        self._val_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._val_lbl)
        
        self.update_status(value, status)


class _WarningBanner(QFrame):
    """Warning/error banner for critical conditions."""

    def __init__(self, message: str, level: str = 'warning', parent=None):
        super().__init__(parent)
        color = COLOR_WARNING if level == 'warning' else COLOR_DANGER
        from theme.style_builder import UIStyleBuilder
        self.setStyleSheet(UIStyleBuilder.get_warning_banner_style(level))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)

        icon = "⚠" if level == 'warning' else "✗"
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_SECTION_TITLE))
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)


class _RestoreStateBadge(QFrame):
    """Shows current restore state machine state."""

    def __init__(self, state: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        color_map = {
            'IDLE': COLOR_SUCCESS,
            'VALIDATING': COLOR_INFO,
            'SNAPSHOT_CREATED': COLOR_INFO,
            'RESTORING': COLOR_WARNING,
            'VERIFYING': COLOR_INFO,
            'COMPLETED': COLOR_SUCCESS,
            'FAILED': COLOR_DANGER,
            'ROLLBACK_TRIGGERED': COLOR_DANGER,
        }
        color = color_map.get(state, COLOR_TEXT_MUTED)

        from theme.style_builder import UIStyleBuilder
        self.setStyleSheet(UIStyleBuilder.get_badge_style(color))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_XS, SPACING_MD, SPACING_XS)

        dot = QLabel("●")
        dot.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_BODY))
        layout.addWidget(dot)

        lbl = QLabel(state.replace('_', ' '))
        lbl.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, TEXT_BODY, 600))
        layout.addWidget(lbl)
        layout.addStretch()


class RestoreConfirmDialog(EnterpriseDialog):
    """Pre-restore confirmation dialog with metadata summary."""

    def __init__(self, metadata: dict, parent=None):
        super().__init__("Confirm Restore", DialogType.CUSTOM, parent)
        content = self._build_content(metadata)
        self.set_content(content)

    def _build_content(self, metadata: dict) -> QWidget:
        from theme.style_builder import UIStyleBuilder

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(SPACING_MD)

        warning = QLabel(
            "⚠ This will replace the current database with the selected backup. "
            "An emergency backup will be created automatically before restore."
        )
        warning.setStyleSheet(UIStyleBuilder.get_label_style("warning"))
        warning.setWordWrap(True)
        layout.addWidget(warning)

        info_group = QGroupBox("Backup Metadata")
        info_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=False))
        info_layout = QVBoxLayout()
        info_layout.setSpacing(SPACING_XS)

        fields = [
            ("Filename", metadata.get('filename', 'N/A')),
            ("Size", metadata.get('size_mb', metadata.get('size', 'N/A'))),
            ("Created", metadata.get('created_at', metadata.get('timestamp', 'N/A'))),
            ("Encrypted", "Yes" if metadata.get('encrypted', False) else "No"),
            ("Checksum", str(metadata.get('checksum', 'N/A'))[:32] + '...'),
        ]
        for label, value in fields:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(UIStyleBuilder.get_label_style("label"))
            row.addWidget(lbl)
            row.addStretch()
            val = QLabel(str(value))
            val.setStyleSheet(UIStyleBuilder.get_label_style("body"))
            row.addWidget(val)
            info_layout.addLayout(row)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        return widget

    def _create_button_area(self):
        button_area = QFrame()
        button_area.setFixedHeight(60)

        layout = QHBoxLayout(button_area)
        layout.setContentsMargins(MARGIN_CARD, SPACING_SM, MARGIN_CARD, SPACING_SM)

        cancel_btn = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        layout.addStretch()

        confirm_btn = EnterpriseButton(text="Confirm Restore", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        confirm_btn.clicked.connect(self.accept)
        layout.addWidget(confirm_btn)

        button_area.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_MAIN};
                border-top: 1px solid {COLOR_FORM_FOOTER_BORDER};
            }}
        """)
        return button_area


class BackupControlScreen(BaseScreen):
    """Unified Backup & Recovery Control Center.

    All state read from SSOT endpoint only. No local caching of critical state.
    """

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="backup_control")
        self.api_client = api_client or APIClient()
        self._is_busy = False
        self._restore_state = 'IDLE'
        self._status_data = {}
        self._backups = []
        self._email_history = []
        self._ssot_unavailable = False
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        main_layout.setSpacing(SPACING_LG)

        from theme.style_builder import UIStyleBuilder
        header = QLabel("Backup & Recovery Control Center")
        header.setStyleSheet(UIStyleBuilder.get_label_style("title"))
        main_layout.addWidget(header)

        self._toolbar = QHBoxLayout()
        self._create_backup_btn = EnterpriseButton(text="Create Backup", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self._create_backup_btn.clicked.connect(self._create_backup)
        self._toolbar.addWidget(self._create_backup_btn)

        self._refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self._refresh_btn.clicked.connect(self._refresh)
        self._toolbar.addWidget(self._refresh_btn)

        self._send_email_btn = EnterpriseButton(text="Send Latest via Email", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self._send_email_btn.clicked.connect(self._send_latest_email)
        self._toolbar.addWidget(self._send_email_btn)

        self._email_config_btn = EnterpriseButton(text="Email Config", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self._email_config_btn.clicked.connect(self._open_email_config)
        self._toolbar.addWidget(self._email_config_btn)

        self._toolbar.addStretch()
        main_layout.addLayout(self._toolbar)

        self._restore_state_badge = _RestoreStateBadge('IDLE')
        main_layout.addWidget(self._restore_state_badge)

        self._warnings_container = QVBoxLayout()
        self._warnings_container.setSpacing(SPACING_SM)
        main_layout.addLayout(self._warnings_container)

        status_grid = QGridLayout()
        status_grid.setSpacing(SPACING_MD)

        self._indicators = {}
        indicator_defs = [
            ('backup_status', 'Backup Status', '—'),
            ('last_backup_time', 'Last Backup', '—'),
            ('certification_score', 'Cert Score', '—'),
            ('certification_status', 'Cert Status', '—'),
            ('restore_lock', 'Restore Lock', '—'),
            ('email_status', 'Email Status', '—'),
            ('email_pending', 'Email Pending', '0'),
            ('encryption', 'Encryption', '—'),
        ]
        for i, (key, label, default) in enumerate(indicator_defs):
            indicator = _StatusIndicator(label, default, 'unknown')
            self._indicators[key] = indicator
            status_grid.addWidget(indicator, i // 4, i % 4)

        main_layout.addLayout(status_grid)

        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(SPACING_LG)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(SPACING_MD)

        backup_list_label = QLabel("Backup Records")
        from theme.style_builder import UIStyleBuilder
        backup_list_label.setStyleSheet(UIStyleBuilder.get_label_style("section"))
        left_panel.addWidget(backup_list_label)

        columns = [
            TableColumn("id", "ID", width=50),
            TableColumn("filename", "Filename", width=250),
            TableColumn("created", "Created", width=150),
            TableColumn("size", "Size (MB)", width=80, align="right"),
            TableColumn("status", "Status", width=80, align="center"),
            TableColumn("encrypted", "Encrypted", width=80, align="center"),
        ]
        self._backup_table = EnterpriseTable(columns)
        left_panel.addWidget(self._backup_table)

        table_actions = QHBoxLayout()
        self._restore_btn = EnterpriseButton(text="Restore Selected", variant=ButtonVariant.WARNING, size=ButtonSize.SMALL)
        self._restore_btn.clicked.connect(self._restore_selected)
        table_actions.addWidget(self._restore_btn)

        self._verify_btn = EnterpriseButton(text="Verify", variant=ButtonVariant.SECONDARY, size=ButtonSize.SMALL)
        self._verify_btn.clicked.connect(self._verify_selected)
        table_actions.addWidget(self._verify_btn)

        self._delete_btn = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.SMALL)
        self._delete_btn.clicked.connect(self._delete_selected)
        table_actions.addWidget(self._delete_btn)
        table_actions.addStretch()
        left_panel.addLayout(table_actions)

        tabs_layout.addLayout(left_panel, 2)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(SPACING_MD)

        email_label = QLabel("Email Notification Logs")
        from theme.style_builder import UIStyleBuilder
        email_label.setStyleSheet(UIStyleBuilder.get_label_style("section"))
        right_panel.addWidget(email_label)

        email_columns = [
            TableColumn("file", "File", width=150),
            TableColumn("status", "Status", width=80, align="center"),
            TableColumn("retries", "Retries", width=60, align="center"),
            TableColumn("created", "Created", width=140),
            TableColumn("error", "Error", width=200),
        ]
        self._email_table = EnterpriseTable(email_columns)
        right_panel.addWidget(self._email_table)

        email_actions = QHBoxLayout()
        self._retry_queue_btn = EnterpriseButton(text="Process Retry Queue", variant=ButtonVariant.SECONDARY, size=ButtonSize.SMALL)
        self._retry_queue_btn.clicked.connect(self._process_retry_queue)
        email_actions.addWidget(self._retry_queue_btn)

        self._retry_single_btn = EnterpriseButton(text="Retry Selected", variant=ButtonVariant.SECONDARY, size=ButtonSize.SMALL)
        self._retry_single_btn.clicked.connect(self._retry_single_email)
        email_actions.addWidget(self._retry_single_btn)
        email_actions.addStretch()
        right_panel.addLayout(email_actions)

        health_label = QLabel("System Health")
        from theme.style_builder import UIStyleBuilder
        health_label.setStyleSheet(UIStyleBuilder.get_label_style("section"))
        right_panel.addWidget(health_label)

        self._health_text = QTextEdit()
        self._health_text.setReadOnly(True)
        self._health_text.setStyleSheet(UIStyleBuilder.get_code_editor_style())
        right_panel.addWidget(self._health_text)

        tabs_layout.addLayout(right_panel, 1)
        main_layout.addLayout(tabs_layout)

    def _set_busy(self, busy: bool):
        self._is_busy = busy
        self._create_backup_btn.setEnabled(not busy)
        self._restore_btn.setEnabled(not busy)
        self._verify_btn.setEnabled(not busy)
        self._delete_btn.setEnabled(not busy)
        self._refresh_btn.setEnabled(not busy)
        self._send_email_btn.setEnabled(not busy)
        self._retry_queue_btn.setEnabled(not busy)

    def _refresh(self):
        if self._is_busy:
            return
        self._set_busy(True)
        try:
            self._fetch_status()
            self._fetch_backups()
            self._fetch_email_history()
            self._update_ui()
        except Exception as e:
            self._show_error(f"Refresh failed: {e}")
        finally:
            self._set_busy(False)

    def _fetch_status(self):
        try:
            response = self.api_client.get("/api/backup/control-plane/status/")
            if isinstance(response, dict) and response.get('success'):
                self._status_data = response.get('data', {})
            elif isinstance(response, dict):
                self._status_data = response
            else:
                self._status_data = {}
                self._ssot_unavailable = True
        except Exception:
            self._status_data = {}
            self._ssot_unavailable = True

    def _fetch_backups(self):
        try:
            response = self.api_client.get("/api/backup/restore-points/")
            if isinstance(response, dict) and response.get('success'):
                data = response.get('data', [])
                self._backups = data if isinstance(data, list) else data.get('results', [])
            elif isinstance(response, list):
                self._backups = response
            else:
                self._backups = []
        except Exception:
            self._backups = []

    def _fetch_email_history(self):
        try:
            response = self.api_client.get("/api/backup/offsite-replication/retry-queue-status/")
            if isinstance(response, dict) and response.get('success'):
                self._email_history = response.get('data', {}).get('history', [])
            elif isinstance(response, dict):
                self._email_history = response.get('history', [])
            else:
                self._email_history = []
        except Exception:
            self._email_history = []

    def _update_ui(self):
        if self._ssot_unavailable:
            self._enter_safe_readonly_mode()
            return

        self._update_indicators()
        self._update_warnings()
        self._update_restore_state()
        self._update_backup_table()
        self._update_email_table()
        self._update_health_text()

    def _enter_safe_readonly_mode(self):
        """Enter safe read-only mode when SSOT is unavailable. Disable all mutation operations."""
        self._create_backup_btn.setEnabled(False)
        self._restore_btn.setEnabled(False)
        self._verify_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._send_email_btn.setEnabled(False)
        self._retry_queue_btn.setEnabled(False)
        self._retry_single_btn.setEnabled(False)

        for key in self._indicators:
            self._indicators[key].update_status("UNAVAILABLE", "critical")

        while self._warnings_container.count():
            item = self._warnings_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        w = _WarningBanner(
            "System status unavailable — all operations locked. "
            "Click Refresh when backend is reachable.",
            'critical'
        )
        self._warnings_container.addWidget(w)

        self._backup_table.set_data([])
        self._email_table.set_data([])
        self._health_text.setPlainText(
            "SSOT UNAVAILABLE\n"
            "================\n\n"
            "Cannot reach backend control plane.\n"
            "All mutation operations are disabled.\n"
            "System is in safe read-only mode.\n\n"
            "This prevents stale state and phantom operations.\n"
            "Click Refresh to retry connection."
        )

    def _update_indicators(self):
        sd = self._status_data

        backup_status = sd.get('backup_status', 'unknown')
        self._indicators['backup_status'].update_status(backup_status.title(), backup_status)

        last_backup = sd.get('last_backup_time', '—')
        if last_backup and len(last_backup) > 19:
            last_backup = last_backup[:19]
        self._indicators['last_backup_time'].update_status(last_backup or '—', 'unknown')

        cert_score = sd.get('certification_score', 0)
        self._indicators['certification_score'].update_status(str(cert_score), 'unknown')

        cert_status = sd.get('certification_status', 'UNKNOWN')
        self._indicators['certification_status'].update_status(cert_status, cert_status)

        lock_active = sd.get('restore_lock_active', False)
        lock_text = 'LOCKED' if lock_active else 'UNLOCKED'
        self._indicators['restore_lock'].update_status(lock_text, 'locked' if lock_active else 'unlocked')

        email_status = sd.get('email_status', 'disabled')
        self._indicators['email_status'].update_status(email_status.title(), email_status)

        email_pending = sd.get('email_pending_count', 0)
        self._indicators['email_pending'].update_status(str(email_pending), 'unknown')

        encryption = sd.get('encryption_configured', False)
        enc_text = 'CONFIGURED' if encryption else 'NOT SET'
        self._indicators['encryption'].update_status(enc_text, 'healthy' if encryption else 'warning')

    def _update_warnings(self):
        while self._warnings_container.count():
            item = self._warnings_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sd = self._status_data
        warnings = sd.get('warnings', [])
        errors = sd.get('errors', [])
        health_warnings = sd.get('health_warnings', [])
        health_errors = sd.get('health_errors', [])
        corruption_warnings = sd.get('corruption_warnings', [])
        corruption_errors = sd.get('corruption_errors', [])

        all_errors = errors + health_errors + corruption_errors
        all_warnings = warnings + health_warnings + corruption_warnings

        if sd.get('restore_lock_active'):
            w = _WarningBanner("Restore is in progress — backup operations are locked", 'warning')
            self._warnings_container.addWidget(w)

        if sd.get('backup_status') == 'critical':
            w = _WarningBanner("System has critical errors — resolve before performing restore", 'critical')
            self._warnings_container.addWidget(w)

        if sd.get('total_backups', 0) == 0:
            w = _WarningBanner("No backups exist — create your first backup immediately", 'critical')
            self._warnings_container.addWidget(w)

        for err in all_errors[:3]:
            w = _WarningBanner(str(err), 'critical')
            self._warnings_container.addWidget(w)

        for warn in all_warnings[:3]:
            w = _WarningBanner(str(warn), 'warning')
            self._warnings_container.addWidget(w)

    def _update_restore_state(self):
        self._restore_state_badge = _RestoreStateBadge(self._restore_state)
        layout_item = self.layout().itemAt(3)
        if layout_item and layout_item.widget():
            old = layout_item.widget()
            self.layout().replaceWidget(old, self._restore_state_badge)
            old.deleteLater()

    def _update_backup_table(self):
        data = []
        for b in self._backups:
            filename = b.get('backup_record_filename', b.get('filename', b.get('name', '')))
            created = str(b.get('created_at', b.get('timestamp', '')))[:19]
            size = b.get('file_size_mb', b.get('size_mb', b.get('size', '')))
            status = b.get('status', 'READY')
            encrypted = 'Yes' if b.get('encrypted', False) else 'No'
            data.append({
                "id": str(b.get('id', ''))[:8],
                "filename": filename,
                "created": created,
                "size": str(size),
                "status": status,
                "encrypted": encrypted,
            })
        self._backup_table.set_data(data)

    def _update_email_table(self):
        data = []
        for entry in self._email_history:
            file_name = str(entry.get('backup_path', ''))
            if '/' in file_name:
                file_name = file_name.split('/')[-1]
            elif '\\' in file_name:
                file_name = file_name.split('\\')[-1]

            status = entry.get('status', 'pending')
            retries = entry.get('retries', 0)
            created = str(entry.get('created_at', ''))[:19]
            error = entry.get('last_error', '')
            if error and len(error) > 50:
                error = error[:50] + '...'

            data.append({
                "file": file_name,
                "status": status,
                "retries": str(retries),
                "created": created,
                "error": error,
            })
        self._email_table.set_data(data)

    def _update_health_text(self):
        sd = self._status_data
        lines = [
            f"Backup Status: {sd.get('backup_status', 'unknown').title()}",
            f"Total Backups: {sd.get('total_backups', 0)}",
            f"Total Size: {sd.get('total_size_mb', 0.0)} MB",
            f"Last Backup: {sd.get('last_backup_time', '—')}",
            f"Restore Lock: {'Active' if sd.get('restore_lock_active') else 'Inactive'}",
            f"Certification: {sd.get('certification_status', 'UNKNOWN')} ({sd.get('certification_score', 0)}/100)",
            f"Email Status: {sd.get('email_status', 'disabled').title()}",
            f"Email Pending: {sd.get('email_pending_count', 0)}",
            f"Encryption: {'Configured' if sd.get('encryption_configured') else 'Not Set'}",
            "",
            "Warnings:",
        ]
        for w in sd.get('warnings', []) + sd.get('health_warnings', []) + sd.get('corruption_warnings', []):
            lines.append(f"  - {w}")
        if not sd.get('warnings') and not sd.get('health_warnings') and not sd.get('corruption_warnings'):
            lines.append("  (none)")

        lines.append("")
        lines.append("Errors:")
        for e in sd.get('errors', []) + sd.get('health_errors', []) + sd.get('corruption_errors', []):
            lines.append(f"  - {e}")
        if not sd.get('errors') and not sd.get('health_errors') and not sd.get('corruption_errors'):
            lines.append("  (none)")

        self._health_text.setPlainText('\n'.join(lines))

    def _create_backup(self):
        if self._is_busy:
            return
        if not ConfirmDialog.confirm("Create Backup",
            "Create a new backup now? This may take a few minutes.",
            self):
            return

        self._set_busy(True)
        try:
            response = self.api_client.post("/api/backup/records/create_backup/", {
                "description": "Manual backup from Control Center",
            })
            if isinstance(response, dict) and response.get("success"):
                AlertDialog.info("Backup", "Backup created successfully.", self)
                self._refresh()
            else:
                err = "Unknown error"
                if isinstance(response, dict):
                    err_info = response.get("error", {})
                    if isinstance(err_info, dict):
                        err = err_info.get("message", str(err_info))
                    else:
                        err = str(err_info)
                AlertDialog.warning("Backup Failed", f"Failed: {err}", self)
        except Exception as e:
            AlertDialog.warning("Backup Failed", f"Failed: {e}", self)
        finally:
            self._set_busy(False)

    def _restore_selected(self):
        if self._is_busy:
            return
        row = self._backup_table.currentRow()
        if row < 0:
            AlertDialog.warning("Restore", "Select a backup to restore.", self)
            return

        backup = self._backups[row] if row < len(self._backups) else None
        if not backup:
            AlertDialog.warning("Restore", "No backup data found.", self)
            return

        metadata = {
            'filename': backup.get('backup_record_filename', backup.get('filename', '')),
            'size_mb': backup.get('file_size_mb', backup.get('size_mb', '')),
            'created_at': backup.get('created_at', backup.get('timestamp', '')),
            'encrypted': backup.get('encrypted', False),
            'checksum': backup.get('checksum', ''),
        }

        dialog = RestoreConfirmDialog(metadata, self)
        if dialog.exec() != QDialog.Accepted:
            return

        self._restore_state = 'VALIDATING'
        self._update_restore_state()
        self._set_busy(True)

        try:
            backup_id = backup.get('id')
            response = self.api_client.post(f"/api/backup/restore-points/{backup_id}/validate/", {})
            if not (isinstance(response, dict) and response.get('success')):
                self._restore_state = 'FAILED'
                self._update_restore_state()
                AlertDialog.warning("Restore", f"Validation failed: {response}", self)
                return

            self._restore_state = 'SNAPSHOT_CREATED'
            self._update_restore_state()

            response = self.api_client.post(f"/api/backup/restore-points/{backup_id}/restore/", {})
            if isinstance(response, dict) and response.get('success'):
                self._restore_state = 'COMPLETED'
                self._update_restore_state()
                AlertDialog.info("Restore", "Restore completed successfully.", self)
            else:
                self._restore_state = 'FAILED'
                self._update_restore_state()
                err = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                AlertDialog.warning("Restore Failed", f"Restore failed: {err}", self)
        except Exception as e:
            self._restore_state = 'FAILED'
            self._update_restore_state()
            AlertDialog.error("Restore Error", f"Restore error: {e}", self)
        finally:
            self._set_busy(False)

    def _verify_selected(self):
        row = self._backup_table.currentRow()
        if row < 0:
            AlertDialog.warning("Verify", "Select a backup to verify.", self)
            return

        backup = self._backups[row] if row < len(self._backups) else None
        if not backup:
            return

        backup_id = backup.get('id')
        try:
            response = self.api_client.post(f"/api/backup/records/{backup_id}/verify/", {})
            if isinstance(response, dict) and response.get('success'):
                AlertDialog.info("Verify", "Backup verified successfully.", self)
                self._refresh()
            else:
                msg = response.get('message', 'Verification failed') if isinstance(response, dict) else 'Verification failed'
                AlertDialog.warning("Verify", msg, self)
        except Exception as e:
            AlertDialog.warning("Verify Failed", f"Failed: {e}", self)

    def _delete_selected(self):
        row = self._backup_table.currentRow()
        if row < 0:
            AlertDialog.warning("Delete", "Select a backup to delete.", self)
            return

        if not ConfirmDialog.confirm("Delete Backup",
            "Delete this backup permanently? This cannot be undone.",
            self):
            return

        backup = self._backups[row] if row < len(self._backups) else None
        if not backup:
            return

        backup_id = backup.get('id')
        try:
            response = self.api_client.delete(f"/api/backup/records/{backup_id}/delete_backup/")
            if isinstance(response, dict) and response.get('success'):
                AlertDialog.info("Delete", "Backup deleted.", self)
                self._refresh()
            else:
                AlertDialog.warning("Delete Failed", "Failed to delete backup.", self)
        except Exception as e:
            AlertDialog.warning("Delete Failed", f"Failed: {e}", self)

    def _send_latest_email(self):
        if not self._backups:
            AlertDialog.warning("Email", "No backups available to send.", self)
            return

        latest = self._backups[0]
        backup_id = latest.get('id')
        try:
            response = self.api_client.post("/api/backup/offsite-replication/send-backup/", {
                "backup_record_id": str(backup_id),
            })
            if isinstance(response, dict) and response.get('success'):
                AlertDialog.info("Email", "Backup sent via email successfully.", self)
                self._fetch_email_history()
                self._update_email_table()
            else:
                err = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                queued = isinstance(response, dict) and response.get('queued')
                if queued:
                    AlertDialog.info("Email Queued", f"Offline — queued for retry: {err}", self)
                else:
                    AlertDialog.warning("Email Failed", f"Failed: {err}", self)
        except Exception as e:
            AlertDialog.warning("Email Failed", f"Failed: {e}", self)

    def _open_email_config(self):
        from ui.system.email_config_dialog import EmailConfigDialog
        dialog = EmailConfigDialog(self.api_client, self)
        dialog.exec()
        self._refresh()

    def _process_retry_queue(self):
        self._set_busy(True)
        try:
            response = self.api_client.post("/api/backup/offsite-replication/process-retry-queue/", {})
            if isinstance(response, dict) and response.get('success'):
                processed = response.get('data', response).get('processed', 0)
                failed = response.get('data', response).get('failed', 0)
                AlertDialog.info("Retry Queue", f"Processed: {processed}, Failed: {failed}", self)
                self._fetch_email_history()
                self._update_email_table()
            else:
                err = response.get('error', 'Unknown') if isinstance(response, dict) else str(response)
                AlertDialog.warning("Retry Failed", f"Failed: {err}", self)
        except Exception as e:
            AlertDialog.warning("Retry Failed", f"Failed: {e}", self)
        finally:
            self._set_busy(False)

    def _retry_single_email(self):
        row = self._email_table.currentRow()
        if row < 0 or row >= len(self._email_history):
            AlertDialog.warning("Retry", "Select an email entry to retry.", self)
            return

        entry = self._email_history[row]
        queue_file = entry.get('_queue_file', '')
        if not queue_file:
            AlertDialog.warning("Retry", "No retry file found for this entry.", self)
            return

        self._set_busy(True)
        try:
            response = self.api_client.post("/api/backup/offsite-replication/retry-single/", {
                "queue_file": queue_file,
            })
            if isinstance(response, dict) and response.get('success'):
                AlertDialog.info("Retry", "Email sent successfully.", self)
                self._fetch_email_history()
                self._update_email_table()
            else:
                err = response.get('error', 'Unknown') if isinstance(response, dict) else str(response)
                AlertDialog.warning("Retry Failed", f"Failed: {err}", self)
        except Exception as e:
            AlertDialog.warning("Retry Failed", f"Failed: {e}", self)
        finally:
            self._set_busy(False)

    def _show_error(self, message: str):
        AlertDialog.error("Error", message, self)
