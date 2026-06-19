"""
Recent Items & Pinned Items System

Minimal implementation for Sprint 3.4 that enhances existing navigation with recent screens
and pinned items functionality.

Key Design Principles:
- Leverages existing navigation infrastructure (NavigationHistory)
- Minimal code changes to existing files
- User-scoped storage (JSON files)
- Backward compatible
- Performance optimized

Architecture:
1. RecentItemsStorage: Handles persistence of recent screens and pinned items
2. NavigationIntegration: Integrates with NavigationHistory
3. Integration Hooks: Add recent item tracking to existing navigation
"""

import json
import logging
import os
import tempfile
import hashlib
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ItemType(Enum):
    """Valid item types for the Recent/Pinned system."""
    SCREEN = "screen"
    REPORT = "report"
    CUSTOMER = "customer"
    PRODUCT = "product"


class RecentItemsStorage:
    """Storage for recent screens and pinned items."""
    
    def __init__(self, user_id: str = "default", max_items: int = 10):
        self.user_id = self._validate_user_id(user_id)
        self.max_items = max_items
        self.storage_file = self._get_storage_file(self.user_id)
        self._ensure_storage_exists()
    
    def _validate_user_id(self, user_id: str) -> str:
        """Validate user_id to prevent path traversal and ensure safe filename.
        
        Security: If user_id contains path traversal sequences (.., /, \\),
        reject it entirely and return 'default'. Do NOT sanitize — reject.
        """
        if not user_id or not isinstance(user_id, str):
            return "default"
        
        # REJECT path traversal attempts — do NOT sanitize
        if ".." in user_id or "/" in user_id or "\\" in user_id:
            logger.warning("Rejected user_id with path traversal: %s", user_id)
            return "default"
        
        # Allow only alphanumeric, underscore, hyphen, dot
        import re
        if not re.fullmatch(r'[a-zA-Z0-9_.\-]+', user_id):
            logger.warning("Rejected user_id with invalid characters: %s", user_id)
            return "default"
        
        # Ensure reasonable length
        if len(user_id) > 50:
            logger.warning("Rejected user_id exceeding length limit: %s", user_id)
            return "default"
        
        return user_id
    
    def _get_storage_file(self, user_id: str) -> str:
        """Get storage file path. Uses ERP_CONFIG_DIR env var if set."""
        config_dir = os.environ.get('ERP_CONFIG_DIR', os.path.expanduser("~/.config/pharmacy_erp"))
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, f"user_{user_id}_recent_items.json")
    
    def _ensure_storage_exists(self):
        """Create storage file with backup if it doesn't exist."""
        if os.path.exists(self.storage_file):
            return
        
        # Create backup of existing file if it somehow exists
        backup_file = self._get_backup_file()
        if os.path.exists(backup_file):
            self._restore_from_backup()
        
        # Create fresh storage
        try:
            data = self._create_fresh_data()
            self._atomic_save_data(data)
        except Exception as e:
            logger.error("Failed to create initial storage file for user %s: %s", self.user_id, e)
            raise
    
    def _create_fresh_data(self) -> Dict:
        """Create fresh data structure."""
        return {
            "recent_screens": {},
            "pinned_items": {}
        }
    
    def _get_backup_file(self) -> str:
        """Get backup file path."""
        return self.storage_file + ".backup"
    
    def _restore_from_backup(self):
        """Restore from backup file if primary is corrupted."""
        backup_file = self._get_backup_file()
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                self._atomic_save_data(backup_data)
                logger.info("Restored recent items data from backup for user %s", self.user_id)
            except Exception as e:
                logger.error("Failed to restore from backup: %s", e)
                raise
    
    def _atomic_save_data(self, data: Dict):
        """Atomically save data to storage using temp file + rename.
        
        Backup strategy: After a successful save, the NEW data is copied to
        the backup file. This ensures that if the primary file is later
        corrupted, recovery restores the most recently saved data.
        """
        # Validate data before writing
        if not self._verify_data_integrity(data):
            raise ValueError("Data failed integrity check — refusing to save")
        
        backup_file = self._get_backup_file()
        temp_file = None
        
        try:
            # Write to temp file first
            temp_file = self._get_temp_file()
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Verify the temp file is valid JSON
            with open(temp_file, 'r', encoding='utf-8') as f:
                json.load(f)
            
            # Atomic rename
            if os.name == 'nt':  # Windows
                if os.path.exists(self.storage_file):
                    os.remove(self.storage_file)
                os.rename(temp_file, self.storage_file)
            else:  # Unix-like
                os.replace(temp_file, self.storage_file)
            
            # Clean up temp file reference
            temp_file = None
            
            # Create backup AFTER successful save (so backup = last known-good data)
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as src, \
                     open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            except Exception as e:
                logger.warning("Could not create backup after save, continuing anyway: %s", e)
            
        except Exception as e:
            logger.error("Atomic save failed for user %s: %s", self.user_id, e)
            
            # Clean up temp file if it exists
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            # Attempt recovery from backup
            self._attempt_recovery_from_backup()
            raise
        
        finally:
            # Clean up temp file if it still exists
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def _attempt_recovery_from_backup(self):
        """Attempt to recover from backup if atomic save failed."""
        backup_file = self._get_backup_file()
        if os.path.exists(backup_file):
            try:
                logger.info("Attempting recovery from backup for user %s", self.user_id)
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                # Verify backup is valid JSON
                self._verify_data_integrity(backup_data)
                
                # Restore backup
                if os.path.exists(self.storage_file):
                    os.remove(self.storage_file)
                os.rename(backup_file, self.storage_file)
                
                logger.info("Successfully recovered recent items from backup for user %s", self.user_id)
                
            except Exception as e:
                logger.error("Recovery from backup failed for user %s: %s", self.user_id, e)
                # If recovery fails, we have corrupted data - clear it
                if os.path.exists(self.storage_file):
                    os.remove(self.storage_file)
    
    def _get_temp_file(self) -> str:
        """Get temporary file path for atomic writes."""
        temp_dir = os.path.expanduser("~/.config/pharmacy_erp")
        return os.path.join(temp_dir, f"user_{self.user_id}_recent_items.tmp")
    
    def _verify_data_integrity(self, data: Dict) -> bool:
        """Verify data integrity before accepting it."""
        if not isinstance(data, dict):
            return False
        
        recent_screens = data.get("recent_screens", {})
        pinned_items = data.get("pinned_items", {})
        
        if not isinstance(recent_screens, dict) or not isinstance(pinned_items, dict):
            return False
        
        # Verify structure of recent screens
        for item_id, item_data in recent_screens.items():
            if not isinstance(item_data, dict):
                return False
            required_fields = ["index", "title", "screen_id", "last_accessed", "type"]
            if not all(field in item_data for field in required_fields):
                return False
        
        # Verify structure of pinned items
        for item_id, item_data in pinned_items.items():
            if not isinstance(item_data, dict):
                return False
            required_fields = ["type", "title", "pinned_at"]
            if not all(field in item_data for field in required_fields):
                return False
        
        return True
    
    def _load_data(self) -> Dict:
        """Load data from storage with corruption recovery."""
        # First try to load the main file
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verify data integrity
            if self._verify_data_integrity(data):
                return data
            else:
                logger.error("Data integrity check failed for user %s, attempting recovery", self.user_id)
                raise ValueError("Data integrity check failed")
                
        except (json.JSONDecodeError, FileNotFoundError, OSError, ValueError) as e:
            logger.warning("Failed to load data for user %s: %s", self.user_id, e)
            
            # Try to recover from backup
            try:
                return self._load_from_backup()
            except Exception as backup_error:
                logger.error("Backup recovery also failed: %s", backup_error)
                # Return safe default
                return {"recent_screens": {}, "pinned_items": {}}
    
    def _load_from_backup(self) -> Dict:
        """Load data from backup file."""
        backup_file = self.get_backup_file()
        if not os.path.exists(backup_file):
            raise FileNotFoundError("No backup file available")
        
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not self._verify_data_integrity(data):
            raise ValueError("Backup data integrity check failed")
        
        logger.info("Loaded data from backup for user %s", self.user_id)
        return data
    
    def get_backup_file(self) -> str:
        """Get backup file path (public method for recovery)."""
        return self._get_backup_file()

    def pin_item(self, item_type: str, item_id: str, title: str) -> bool:
        """Pin an item."""
        data = self._load_data()
        data.setdefault("pinned_items", {})
        
        full_item_id = f"{item_type}_{item_id}"
        
        if full_item_id in data["pinned_items"]:
            # Already pinned
            return False
        
        # Pin
        data["pinned_items"][full_item_id] = {
            "type": item_type,
            "title": title,
            "pinned_at": datetime.now().isoformat()
        }
        self._atomic_save_data(data)
        return True

    def unpin_item(self, item_type: str, item_id: str) -> bool:
        """Unpin an item."""
        data = self._load_data()
        full_item_id = f"{item_type}_{item_id}"
        
        if full_item_id not in data.get("pinned_items", {}):
            return False
        
        del data["pinned_items"][full_item_id]
        self._atomic_save_data(data)
        return True

    def get_all_pinned(self) -> List[Dict]:
        """Get all pinned items."""
        data = self._load_data()
        pinned = data.get("pinned_items", {})
        
        result = []
        for item_id, item_data in pinned.items():
            result.append({
                "id": item_id,
                "title": item_data["title"],
                "type": item_data["type"],
                "pinned_at": item_data["pinned_at"]
            })
        return result

    def clear_pinned_items(self) -> None:
        """Clear all pinned items."""
        data = self._load_data()
        data["pinned_items"] = {}
        self._atomic_save_data(data)

    def get_recent_items(self, item_type: str, limit: int = 10) -> List[Dict]:
        """Get recent items of a specific type."""
        data = self._load_data()
        items = data.get("recent_screens", {})
        
        result = []
        for item_id, item_data in items.items():
            if item_data["type"] == item_type:
                result.append({
                    "id": item_id,
                    "title": item_data["title"],
                    "type": item_data["type"],
                    "last_accessed": item_data["last_accessed"]
                })
        
        result.sort(key=lambda x: x["last_accessed"], reverse=True)
        return result[:limit]

    def add_screen(self, index: int, title: str, screen_id: str) -> None:
        """Add screen to recent items."""
        data = self._load_data()
        item_id = f"screen_{screen_id}"
        
        data["recent_screens"][item_id] = {
            "index": index,
            "title": title,
            "screen_id": screen_id,
            "last_accessed": datetime.now().isoformat(),
            "type": "screen"
        }
        
        # Keep only most recent items
        if len(data["recent_screens"]) > self.max_items:
            items = sorted(data["recent_screens"].items(), 
                         key=lambda x: x[1]["last_accessed"], reverse=True)
            data["recent_screens"] = dict(items[:self.max_items])
        
        self._atomic_save_data(data)

    def toggle_pin(self, item_type: str, item_id: str, title: str) -> bool:
        """Toggle pin state for an item.
        
        Returns:
            True if item is now pinned, False if unpinned
        """
        data = self._load_data()
        data.setdefault("pinned_items", {})
        
        full_item_id = f"{item_type}_{item_id}"
        
        if full_item_id in data["pinned_items"]:
            # Unpin
            del data["pinned_items"][full_item_id]
            self._atomic_save_data(data)
            return False
        else:
            # Pin
            data["pinned_items"][full_item_id] = {
                "type": item_type,
                "title": title,
                "pinned_at": datetime.now().isoformat()
            }
            self._atomic_save_data(data)
            return True

    def is_pinned(self, item_type: str, item_id: str) -> bool:
        """Check if item is pinned."""
        data = self._load_data()
        full_item_id = f"{item_type}_{item_id}"
        return full_item_id in data.get("pinned_items", {})

    def get_recent_screens(self) -> List[Dict]:
        """Get recent screens sorted by last access."""
        data = self._load_data()
        screens = data.get("recent_screens", {})
        items = list(screens.values())
        items.sort(key=lambda x: x["last_accessed"], reverse=True)
        return items

    def get_pinned_items(self, item_type: str) -> List[Dict]:
        """Get pinned items of a specific type."""
        data = self._load_data()
        pinned = data.get("pinned_items", {})
        
        result = []
        for item_id, item_data in pinned.items():
            if item_data["type"] == item_type:
                result.append({
                    "id": item_id,
                    "title": item_data["title"],
                    "type": item_data["type"],
                    "pinned_at": item_data["pinned_at"]
                })
        return result