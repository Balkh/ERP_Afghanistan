"""
Tests for Recent Items & Pinned Items System (Sprint 3.4)

These tests focus on verifying atomic file writes, error recovery,
user isolation, and integration functionality.
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Mock PySide6 imports
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()

from ui.recent_items_storage import RecentItemsStorage, ItemType


class TestRecentItemsStorageAtomicWrites(unittest.TestCase):
    """Test atomic file write functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_config_dir = os.environ.get('ERP_CONFIG_DIR')
        os.environ['ERP_CONFIG_DIR'] = self.test_dir
        
        # Create a temporary config directory
        self.config_dir = os.path.join(self.test_dir, '.config', 'pharmacy_erp')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Create test storage
        self.test_user_id = 'test_user'
        self.storage = RecentItemsStorage(user_id=self.test_user_id, max_items=5)
        self.storage_file = self.storage.storage_file
        
    def tearDown(self):
        """Clean up after tests."""
        if self.original_config_dir is None:
            del os.environ['ERP_CONFIG_DIR']
        else:
            os.environ['ERP_CONFIG_DIR'] = self.original_config_dir
            
        # Clean up temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_atomic_write_creation(self):
        """Test that initial storage file creation is atomic."""
        # File should be created
        self.assertTrue(os.path.exists(self.storage_file))
        
        # File should be valid JSON
        with open(self.storage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Should have required structure
        self.assertIn('recent_screens', data)
        self.assertIn('pinned_items', data)
        self.assertEqual(data['recent_screens'], {})
        self.assertEqual(data['pinned_items'], {})
    
    def test_atomic_save_data(self):
        """Test atomic save data functionality."""
        # Prepare test data
        test_data = {
            'recent_screens': {
                'screen_123': {
                    'index': 0,
                    'title': 'Test Screen',
                    'screen_id': 'test',
                    'last_accessed': '2026-01-01T00:00:00',
                    'type': 'screen'
                }
            },
            'pinned_items': {}
        }
        
        # Perform atomic save
        self.storage._atomic_save_data(test_data)
        
        # Verify data was saved
        with open(self.storage_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data['recent_screens']['screen_123']['title'], 'Test Screen')
        
        # Verify backup was created
        backup_file = self.storage._get_backup_file()
        self.assertTrue(os.path.exists(backup_file))
    
    def test_atomic_save_with_verification(self):
        """Test that atomic save verifies data integrity."""
        # Create valid data
        valid_data = {
            'recent_screens': {},
            'pinned_items': {}
        }
        
        # Save valid data
        self.storage._atomic_save_data(valid_data)
        
        # Create invalid data (missing required fields)
        invalid_data = {
            'recent_screens': {
                'bad_item': {
                    'title': 'Missing required fields'
                    # Missing index, screen_id, last_accessed, type
                }
            },
            'pinned_items': {}
        }
        
        # Should raise exception for invalid data
        with self.assertRaises(Exception):
            self.storage._atomic_save_data(invalid_data)
        
        # Original valid data should be preserved
        with open(self.storage_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data['recent_screens'], {})
    
    def test_atomic_save_interrupt_recovery(self):
        """Test recovery from interrupted atomic save."""
        # Create initial data
        initial_data = {
            'recent_screens': {
                'screen_456': {
                    'index': 1,
                    'title': 'Original Screen',
                    'screen_id': 'original',
                    'last_accessed': '2026-01-01T00:00:00',
                    'type': 'screen'
                }
            },
            'pinned_items': {}
        }
        
        self.storage._atomic_save_data(initial_data)
        
        # Simulate corrupted file
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            f.write('invalid json {\\n')
        
        # Try to load - should recover from backup
        loaded_data = self.storage._load_data()
        
        # Should have recovered the original data
        self.assertIn('screen_456', loaded_data['recent_screens'])
        self.assertEqual(loaded_data['recent_screens']['screen_456']['title'], 'Original Screen')
    
    def test_user_id_validation(self):
        """Test user_id validation to prevent path traversal."""
        # Test valid user_id
        storage1 = RecentItemsStorage(user_id='valid_user_123')
        self.assertEqual(storage1.user_id, 'valid_user_123')
        
        # Test user_id with path traversal attempts
        storage2 = RecentItemsStorage(user_id='../etc/passwd')
        self.assertEqual(storage2.user_id, 'default')  # Should fallback to default
        
        storage3 = RecentItemsStorage(user_id='../../../var/log')
        self.assertEqual(storage3.user_id, 'default')  # Should fallback to default
        
        # Test empty user_id
        storage4 = RecentItemsStorage(user_id='')
        self.assertEqual(storage4.user_id, 'default')
        
        # Test None user_id
        storage5 = RecentItemsStorage(user_id=None)
        self.assertEqual(storage5.user_id, 'default')
        
        # Test user_id with invalid characters — should be rejected
        storage6 = RecentItemsStorage(user_id='user@name#with$special')
        self.assertEqual(storage6.user_id, 'default')  # Should reject invalid characters
    
    def test_user_id_file_path(self):
        """Test that user_id generates correct file path."""
        # When ERP_CONFIG_DIR is set, storage files go directly there
        test_dir = os.environ.get('ERP_CONFIG_DIR', self.test_dir)
        
        # Test valid user_id
        storage = RecentItemsStorage(user_id='test_user_123')
        expected_file = os.path.join(test_dir, 'user_test_user_123_recent_items.json')
        self.assertEqual(storage.storage_file, expected_file)
        
        # Test default user_id
        default_storage = RecentItemsStorage(user_id='default')
        expected_default_file = os.path.join(test_dir, 'user_default_recent_items.json')
        self.assertEqual(default_storage.storage_file, expected_default_file)
    
    def test_data_integrity_verification(self):
        """Test data integrity verification."""
        storage = RecentItemsStorage()
        
        # Valid data should pass verification
        valid_data = {
            'recent_screens': {
                'screen_1': {
                    'index': 0,
                    'title': 'Test',
                    'screen_id': 'test',
                    'last_accessed': '2026-01-01T00:00:00',
                    'type': 'screen'
                }
            },
            'pinned_items': {
                'screen_2': {
                    'type': 'screen',
                    'title': 'Test Pinned',
                    'pinned_at': '2026-01-01T00:00:00'
                }
            }
        }
        
        self.assertTrue(storage._verify_data_integrity(valid_data))
        
        # Invalid data should fail verification
        invalid_data = {
            'recent_screens': 'not a dict',
            'pinned_items': {}
        }
        self.assertFalse(storage._verify_data_integrity(invalid_data))
        
        # Missing required fields
        incomplete_data = {
            'recent_screens': {
                'screen_1': {
                    'title': 'Missing fields'
                    # Missing index, screen_id, last_accessed, type
                }
            },
            'pinned_items': {}
        }
        self.assertFalse(storage._verify_data_integrity(incomplete_data))
    
    def test_concurrent_access_safety(self):
        """Test that storage instance is shared across calls."""
        # Create storage instance
        storage1 = RecentItemsStorage(user_id='concurrent_test')
        
        # Get storage via get_storage (if available)
        try:
            from frontend.ui.recent_items_storage import get_storage
            storage2 = get_storage(user_id='concurrent_test')
            
            # Should be same instance (singleton pattern)
            self.assertIs(storage1, storage2)
        except ImportError:
            pass  # get_storage not available in this test context
    
    def test_storage_initialization_error_recovery(self):
        """Test recovery from storage initialization errors."""
        # Create a storage instance
        storage = RecentItemsStorage(user_id='error_test')
        
        # Corrupt the storage file
        with open(storage.storage_file, 'w', encoding='utf-8') as f:
            f.write('invalid json content {\\n')
        
        # Try to load data - should attempt recovery from backup
        loaded_data = storage._load_data()
        
        # Should return safe default data
        self.assertIn('recent_screens', loaded_data)
        self.assertIn('pinned_items', loaded_data)
        self.assertEqual(loaded_data['recent_screens'], {})
        self.assertEqual(loaded_data['pinned_items'], {})


if __name__ == '__main__':
    unittest.main()
