"""Simple caching utility for ERP frontend."""
import time
from typing import Any, Optional, Callable
from threading import Lock


class CacheEntry:
    """Represents a single cache entry."""
    
    def __init__(self, value: Any, ttl: float = 300.0):  # Default 5 minutes TTL
        self.value = value
        self.expiry = time.time() + ttl
        self.hits = 0
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > self.expiry
    
    def get_value(self) -> Any:
        """Get the cached value and increment hit counter."""
        self.hits += 1
        return self.value


class Cache:
    """Thread-safe cache with TTL support."""
    
    def __init__(self, default_ttl: float = 300.0):
        self._cache = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired():
                    del self._cache[key]
                    return None
                return entry.get_value()
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in cache."""
        if ttl is None:
            ttl = self.default_ttl
        with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values()
                if entry.is_expired()
            )
            total_hits = sum(entry.hits for entry in self._cache.values())
            
            return {
                "total_entries": total_entries,
                "active_entries": total_entries - expired_entries,
                "expired_entries": expired_entries,
                "total_hits": total_hits
            }


# Global cache instance
app_cache = Cache(default_ttl=60.0)  # Default 1 minute for UI data


def cached(ttl: float = 60.0):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            result = app_cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            app_cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator