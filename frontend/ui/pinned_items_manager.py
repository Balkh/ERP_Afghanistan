"""
Pinned Items Manager

Business logic for managing pinned items in the Recent Items & Pinned Items System.

Part of SPRINT 3.4 — Recent Items & Pinned Items System
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from .recent_items_storage import RecentItemsStorage, ItemType


class PinnedItemsManager:
    """
    Manage pinned items with validation and deduplication.
    
    Features:
    - Toggle pin state for items
    - Validation and business rules
    - Fast lookup methods
    - Integration with RecentItemsStorage
    """
    
    def __init__(self, storage: RecentItemsStorage):
        """
        Initialize the Pinned Items Manager.
        
        Args:
            storage: RecentItemsStorage instance
        """
        self._storage = storage
    
    def toggle_pin(self, item_type: str, item_id: str, title: str) -> bool:
        """Toggle pin state for an item.
        
        Args:
            item_type: Type of item (screen, report, customer, product)
            item_id: Unique identifier for the item
            title: Display title for the item
            
        Returns:
            True if item is now pinned, False if unpinned
        """
        is_pinned = self._storage.is_pinned(item_type, item_id)
        
        if is_pinned:
            # Unpin the item
            self._storage.unpin_item(item_type, item_id)
            return False
        else:
            # Pin the item
            self._storage.pin_item(item_type, item_id, title)
            return True
    
    def pin_item(self, item_type: str, item_id: str, title: str) -> bool:
        """Pin an item.
        
        Args:
            item_type: Type of item (screen, report, customer, product)
            item_id: Unique identifier for the item
            title: Display title for the item
            
        Returns:
            True if item was pinned, False if already pinned
        """
        if self._storage.is_pinned(item_type, item_id):
            return False
            
        self._storage.pin_item(item_type, item_id, title)
        return True
    
    def unpin_item(self, item_type: str, item_id: str) -> bool:
        """Unpin an item.
        
        Args:
            item_type: Type of item (screen, report, customer, product)
            item_id: Unique identifier for the item
            
        Returns:
            True if item was unpinned, False if not pinned
        """
        return self._storage.unpin_item(item_type, item_id)
    
    def is_pinned(self, item_type: str, item_id: str) -> bool:
        """Check if an item is pinned.
        
        Args:
            item_type: Type of item (screen, report, customer, product)
            item_id: Unique identifier for the item
            
        Returns:
            True if item is pinned, False otherwise
        """
        return self._storage.is_pinned(item_type, item_id)
    
    def get_pinned_items(self, item_type: str) -> List[Dict]:
        """Get all pinned items of a specific type.
        
        Args:
            item_type: Type of item (screen, report, customer, product)
            
        Returns:
            List of pinned items with metadata
        """
        return self._storage.get_pinned_items(item_type)
    
    def get_all_pinned_items(self) -> List[Dict]:
        """Get all pinned items across all types.
        
        Returns:
            List of all pinned items with metadata
        """
        return self._storage.get_all_pinned()
    
    def pin_from_recent(self, item_type: str, item_id: str, title: str) -> bool:
        """Pin an item from recent items.
        
        Args:
            item_type: Type of item (screen, report, customer, product)
            item_id: Unique identifier for the item
            title: Display title for the item
            
        Returns:
            True if item was pinned, False if already pinned or not found
        """
        # Check if item exists in recent items
        recent_items = self._storage.get_recent_items(item_type)
        item_found = any(item.get("id") == item_id for item in recent_items)
        
        if not item_found:
            return False
            
        return self.pin_item(item_type, item_id, title)
    
    def unpin_to_recent(self, item_type: str, item_id: str) -> bool:
        """Move a pinned item to recent items (unpin to recent).
        
        Args:
            item_type: Type of item (screen, report, customer, product)
            item_id: Unique identifier for the item
            
        Returns:
            True if item was unpin and moved to recent, False if not pinned or not found
        """
        if not self.is_pinned(item_type, item_id):
            return False
            
        # Get item metadata from storage
        # This is a simplified version - in a real implementation,
        # you might want to store additional metadata
        self.unpin_item(item_type, item_id)
        return True
    
    def get_pinned_counts(self) -> Dict[str, int]:
        """Get counts of pinned items by type.
        
        Returns:
            Dictionary with counts for each item type
        """
        counts = {}
        for item_type in ItemType:
            counts[item_type.value] = len(self.get_pinned_items(item_type.value))
        return counts
    
    def clear_pinned_items(self) -> None:
        """Clear all pinned items."""
        self._storage.clear_pinned_items()
    
    def has_pinned_items(self) -> bool:
        """Check if there are any pinned items.
        
        Returns:
            True if there are pinned items, False otherwise
        """
        return len(self.get_all_pinned_items()) > 0
    
    def get_pinned_summary(self) -> Dict[str, Any]:
        """Get a summary of pinned items.
        
        Returns:
            Dictionary with summary information
        """
        counts = self.get_pinned_counts()
        total_pinned = sum(counts.values())
        
        return {
            "total_pinned": total_pinned,
            "counts_by_type": counts,
            "has_pinned_items": self.has_pinned_items(),
            "most_common_type": max(counts.items(), key=lambda x: x[1], default=("none", 0))[0]
        }