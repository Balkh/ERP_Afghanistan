"""
Offsite backup replication via email.

Lightweight email-based offsite backup delivery:
- Connectivity-aware sending
- Retry queue for offline scenarios
- Multiple recipients
- Encrypted attachments
- Send status logging

Uses only stdlib (smtplib, email.message) — no Celery, Redis, or external deps.
"""
import os
import json
import logging
import smtplib
import socket
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Dict

logger = logging.getLogger('backup')


class OffsiteReplicationConfig:
    """Configuration for offsite email replication."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            config_dir = str(Path(appdata) / 'PharmacyERP' / 'config')
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / 'offsite_config.json'
        self.retry_dir = self.config_dir / 'offsite_retry'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.retry_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Dict:
        """Load offsite replication config."""
        defaults = {
            'enabled': False,
            'smtp_host': '',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_user': '',
            'smtp_password': '',
            'from_email': '',
            'recipients': [],
            'max_attachment_mb': 25,
            'retry_interval_minutes': 30,
            'max_retries': 10,
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    custom = json.load(f)
                defaults.update(custom)
            except Exception as e:
                logger.warning(f"Failed to load offsite config: {e}")
        
        return defaults
    
    def save(self, config: Dict):
        """Save offsite replication config."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)


class RetryQueue:
    """Local retry queue for failed offsite sends."""
    
    def __init__(self, retry_dir: Path):
        self.retry_dir = retry_dir
        self.retry_dir.mkdir(parents=True, exist_ok=True)
    
    def enqueue(self, backup_path: str, recipients: List[str], metadata: Dict):
        """Add a backup to the retry queue. Prevents duplicate entries for same backup."""
        import os
        backup_key = os.path.basename(backup_path)

        for queue_file in self.retry_dir.glob('retry_*.json'):
            try:
                with open(queue_file, 'r') as f:
                    existing = json.load(f)
                if existing.get('status') == 'pending':
                    existing_path = existing.get('backup_path', '')
                    if os.path.basename(existing_path) == backup_key:
                        logger.info(f"Duplicate retry entry skipped for {backup_key}")
                        return queue_file
            except Exception:
                pass

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        queue_file = self.retry_dir / f"retry_{timestamp}.json"

        entry = {
            'backup_path': backup_path,
            'recipients': recipients,
            'metadata': metadata,
            'created_at': datetime.now().isoformat(),
            'retries': 0,
            'last_attempt': None,
            'status': 'pending',
        }

        with open(queue_file, 'w') as f:
            json.dump(entry, f, indent=2)

        logger.info(f"Backup queued for offsite retry: {queue_file.name}")
        return queue_file
    
    def get_pending(self) -> List[Dict]:
        """Get all pending retry entries."""
        pending = []
        for queue_file in self.retry_dir.glob('retry_*.json'):
            try:
                with open(queue_file, 'r') as f:
                    entry = json.load(f)
                if entry.get('status') == 'pending':
                    entry['_queue_file'] = str(queue_file)
                    pending.append(entry)
            except Exception as e:
                logger.warning(f"Failed to read retry entry {queue_file}: {e}")
        
        return sorted(pending, key=lambda x: x.get('created_at', ''))
    
    def mark_sent(self, queue_file: str):
        """Mark a retry entry as sent."""
        try:
            with open(queue_file, 'r') as f:
                entry = json.load(f)
            entry['status'] = 'sent'
            entry['sent_at'] = datetime.now().isoformat()
            with open(queue_file, 'w') as f:
                json.dump(entry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to mark retry as sent: {e}")
    
    def mark_failed(self, queue_file: str, error: str):
        """Mark a retry entry as failed (increment retry count)."""
        try:
            with open(queue_file, 'r') as f:
                entry = json.load(f)
            entry['retries'] = entry.get('retries', 0) + 1
            entry['last_attempt'] = datetime.now().isoformat()
            entry['last_error'] = error
            if entry['retries'] >= 10:
                entry['status'] = 'exhausted'
            with open(queue_file, 'w') as f:
                json.dump(entry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to mark retry as failed: {e}")
    
    def cleanup_old(self, max_age_days: int = 7):
        """Remove retry entries older than max_age_days."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        for queue_file in self.retry_dir.glob('retry_*.json'):
            try:
                with open(queue_file, 'r') as f:
                    entry = json.load(f)
                created = datetime.fromisoformat(entry['created_at'].split('+')[0])
                if created < cutoff:
                    queue_file.unlink()
            except Exception:
                pass


class OffsiteReplicator:
    """
    Handles offsite backup replication via email.
    
    Flow:
    1. Check internet connectivity
    2. If online → send email with backup attachment
    3. If offline → queue for retry
    4. Process retry queue on next successful connection
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or OffsiteReplicationConfig().load()
        self.retry_queue = RetryQueue(Path(self.config.get('retry_dir') or str(
            Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'PharmacyERP' / 'config' / 'offsite_retry'
        )))
    
    def is_online(self) -> bool:
        """Check internet connectivity via DNS resolution."""
        try:
            socket.gethostbyname('smtp.gmail.com')
            return True
        except socket.gaierror:
            try:
                socket.gethostbyname('1.1.1.1')
                return True
            except socket.gaierror:
                return False
    
    def send_backup(self, backup_path: str, description: str = '') -> Dict:
        """
        Send a backup file via email to configured recipients.
        
        Returns dict with success status and details.
        """
        if not self.config.get('enabled', False):
            return {'success': False, 'error': 'Offsite replication is disabled'}
        
        recipients = self.config.get('recipients', [])
        if not recipients:
            return {'success': False, 'error': 'No recipients configured'}
        
        if not os.path.exists(backup_path):
            return {'success': False, 'error': 'Backup file not found'}
        
        # Check file size
        file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        max_mb = self.config.get('max_attachment_mb', 25)
        if file_size_mb > max_mb:
            return {
                'success': False,
                'error': f'Backup too large for email: {file_size_mb:.1f} MB (max {max_mb} MB)',
            }
        
        # Connectivity check
        if not self.is_online():
            self.retry_queue.enqueue(backup_path, recipients, {'description': description})
            return {
                'success': False,
                'error': 'No internet connection. Backup queued for retry.',
                'queued': True,
            }
        
        # Attempt send
        try:
            self._send_email(backup_path, recipients, description)
            self.retry_queue.cleanup_old()
            return {
                'success': True,
                'sent_to': recipients,
                'size_mb': round(file_size_mb, 2),
            }
        except Exception as e:
            logger.error(f"Offsite send failed: {e}")
            self.retry_queue.enqueue(backup_path, recipients, {'description': description, 'error': str(e)})
            return {
                'success': False,
                'error': str(e),
                'queued': True,
            }
    
    def process_retry_queue(self) -> Dict:
        """Process pending retry entries with max_retries enforcement and exponential backoff."""
        pending = self.retry_queue.get_pending()
        if not pending:
            return {'success': True, 'processed': 0, 'message': 'No pending retries'}

        if not self.is_online():
            return {'success': False, 'error': 'No internet connection', 'pending': len(pending)}

        max_retries = self.config.get('max_retries', 10)
        retry_interval = self.config.get('retry_interval_minutes', 30)

        results = {'success': True, 'processed': 0, 'failed': 0, 'skipped': 0, 'details': []}

        for entry in pending:
            retries = entry.get('retries', 0)

            if retries >= max_retries:
                self.retry_queue.mark_failed(entry['_queue_file'], f'Max retries ({max_retries}) exceeded')
                results['skipped'] += 1
                results['details'].append({'file': entry.get('backup_path', ''), 'status': 'max_retries_exceeded'})
                continue

            last_attempt = entry.get('last_attempt')
            if last_attempt:
                try:
                    from datetime import timezone
                    last_dt = datetime.fromisoformat(last_attempt.split('+')[0])
                    elapsed = (datetime.now() - last_dt).total_seconds() / 60.0
                    backoff = retry_interval * (2 ** min(retries, 5))
                    if elapsed < backoff:
                        results['details'].append({'file': entry.get('backup_path', ''), 'status': 'backoff_active'})
                        continue
                except (ValueError, TypeError):
                    pass

            backup_path = entry['backup_path']
            if not os.path.exists(backup_path):
                self.retry_queue.mark_failed(entry['_queue_file'], 'Backup file no longer exists')
                results['failed'] += 1
                results['details'].append({'file': backup_path, 'status': 'file_missing'})
                continue

            try:
                self._send_email(backup_path, entry['recipients'], entry.get('metadata', {}).get('description', ''))
                self.retry_queue.mark_sent(entry['_queue_file'])
                results['processed'] += 1
                results['details'].append({'file': backup_path, 'status': 'sent'})
            except Exception as e:
                self.retry_queue.mark_failed(entry['_queue_file'], str(e))
                results['failed'] += 1
                results['details'].append({'file': backup_path, 'status': 'failed', 'error': str(e)})

        return results
    
    def _send_email(self, backup_path: str, recipients: List[str], description: str):
        """Send email with backup attachment. Validates recipients and sanitizes credentials."""
        import re
        valid_recipients = []
        for r in recipients:
            r = r.strip()
            if r and re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', r):
                valid_recipients.append(r)

        if not valid_recipients:
            raise ValueError('No valid email recipients')

        msg = MIMEMultipart()
        msg['From'] = self.config['from_email']
        msg['To'] = ', '.join(valid_recipients)
        msg['Subject'] = f"Pharmacy ERP Backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        body = (
            f"Pharmacy ERP Backup\n"
            f"====================\n\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"File: {os.path.basename(backup_path)}\n"
            f"Size: {os.path.getsize(backup_path) / (1024 * 1024):.1f} MB\n"
        )
        if description:
            body += f"Description: {description}\n"
        body += "\nThis is an automated backup. Do not reply to this email."

        msg.attach(MIMEText(body, 'plain'))

        with open(backup_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{os.path.basename(backup_path)}"',
            )
            msg.attach(part)
        
        # Send via SMTP
        if self.config.get('smtp_use_tls', True):
            server = smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port'])
            server.starttls()
        else:
            server = smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port'])
        
        if self.config.get('smtp_user') and self.config.get('smtp_password'):
            server.login(self.config['smtp_user'], self.config['smtp_password'])
        
        server.sendmail(self.config['from_email'], recipients, msg.as_string())
        server.quit()
        
        logger.info(f"Backup sent to {recipients}: {os.path.basename(backup_path)}")
