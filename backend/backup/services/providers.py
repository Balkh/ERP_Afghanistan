"""
File system abstraction providers for RestoreService.

These abstractions allow:
- Production filesystem access
- Fully mockable testing without disk I/O
- Easy swapping of implementations
"""
import hashlib
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class FileProvider(ABC):
    """Abstraction for file system operations."""
    
    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        pass
    
    @abstractmethod
    def read_text(self, file_path: str) -> str:
        """Read file contents as text."""
        pass
    
    @abstractmethod
    def read_bytes(self, file_path: str) -> bytes:
        """Read file contents as bytes."""
        pass


class ChecksumProvider(ABC):
    """Abstraction for checksum operations."""
    
    @abstractmethod
    def calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        pass
    
    @abstractmethod
    def verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """Verify file checksum matches expected value."""
        pass


class ArchiveProvider(ABC):
    """Abstraction for archive validation operations."""
    
    @abstractmethod
    def get_extension(self, file_path: str) -> str:
        """Get file extension."""
        pass
    
    @abstractmethod
    def is_valid_archive(self, file_path: str) -> bool:
        """Check if file has valid archive extension."""
        pass
    
    @abstractmethod
    def is_sql_file(self, file_path: str) -> bool:
        """Check if file is SQL format."""
        pass
    
    @abstractmethod
    def validate_sql_content(self, file_path: str, required_tables: list) -> Dict[str, Any]:
        """Validate SQL file contains required tables."""
        pass
    
    @abstractmethod
    def validate_transaction_integrity(self, file_path: str) -> Dict[str, Any]:
        """Validate SQL file transaction integrity."""
        pass


class ProductionFileProvider(FileProvider):
    """Production implementation using actual filesystem."""
    
    def exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)
    
    def get_size(self, file_path: str) -> int:
        return os.path.getsize(file_path)
    
    def read_text(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def read_bytes(self, file_path: str) -> bytes:
        with open(file_path, 'rb') as f:
            return f.read()


class ProductionChecksumProvider(ChecksumProvider):
    """Production implementation using hashlib."""
    
    def calculate_sha256(self, file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        calculated = self.calculate_sha256(file_path)
        return calculated == expected_checksum


class ProductionArchiveProvider(ArchiveProvider):
    """Production implementation using os.path."""
    
    VALID_EXTENSIONS = ['.sql', '.dump', '.gz', '.zip', '.tar', '.tgz']
    
    def get_extension(self, file_path: str) -> str:
        return os.path.splitext(file_path)[1].lower()
    
    def is_valid_archive(self, file_path: str) -> bool:
        return self.get_extension(file_path) in self.VALID_EXTENSIONS
    
    def is_sql_file(self, file_path: str) -> bool:
        return file_path.lower().endswith('.sql')
    
    def validate_sql_content(self, file_path: str, required_tables: list) -> Dict[str, Any]:
        try:
            content = self.read_text(file_path)
            missing_tables = [t for t in required_tables if t not in content]
            return {
                'valid': len(missing_tables) == 0,
                'missing_tables': missing_tables,
                'checked_tables': required_tables,
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
            }
    
    def validate_transaction_integrity(self, file_path: str) -> Dict[str, Any]:
        try:
            content = self.read_text(file_path)
            issues = []
            
            if 'BEGIN;' not in content and 'BEGIN' not in content:
                issues.append('No transaction blocks found')
            
            begin_count = content.count('BEGIN')
            if begin_count > 0:
                if begin_count != content.count('COMMIT') and begin_count != content.count('ROLLBACK'):
                    issues.append('Unmatched transaction statements')
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
            }
    
    def read_text(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()


class MockFileProvider(FileProvider):
    """Mock implementation for testing - no disk access."""
    
    def __init__(self, files: Dict[str, Dict[str, Any]] = None):
        """
        Args:
            files: Dict mapping file_path to {exists, size, content}
        """
        self._files = files or {}
    
    def add_file(self, file_path: str, exists: bool = True, size: int = 0, content: str = ''):
        self._files[file_path] = {
            'exists': exists,
            'size': size,
            'content': content,
        }
    
    def exists(self, file_path: str) -> bool:
        return self._files.get(file_path, {}).get('exists', False)
    
    def get_size(self, file_path: str) -> int:
        return self._files.get(file_path, {}).get('size', 0)
    
    def read_text(self, file_path: str) -> str:
        return self._files.get(file_path, {}).get('content', '')
    
    def read_bytes(self, file_path: str) -> bytes:
        content = self._files.get(file_path, {}).get('content', '')
        return content.encode('utf-8') if isinstance(content, str) else content


class MockChecksumProvider(ChecksumProvider):
    """Mock implementation for testing - no real checksum computation."""
    
    def __init__(self, checksums: Dict[str, str] = None):
        """
        Args:
            checksums: Dict mapping file_path to checksum (simple string -> string)
        """
        self._checksums = checksums or {}
    
    def add_checksum(self, file_path: str, checksum: str):
        self._checksums[file_path] = checksum
    
    def calculate_sha256(self, file_path: str) -> str:
        # Return stored checksum or compute from content
        stored = self._checksums.get(file_path, '')
        if stored:
            return stored
        # Fallback to hash of empty string if not found
        return hashlib.sha256(b'').hexdigest()
    
    def verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        stored = self._checksums.get(file_path, '')
        return stored == expected_checksum


class MockArchiveProvider(ArchiveProvider):
    """Mock implementation for testing - no real archives."""
    
    def __init__(self, archives: Dict[str, Dict[str, Any]] = None):
        """
        Args:
            archives: Dict mapping file_path to archive metadata
        """
        self._archives = archives or {}
    
    def add_archive(self, file_path: str, extension: str, sql_content: str = '',
                   tables: list = None, transactions_valid: bool = True):
        self._archives[file_path] = {
            'extension': extension,
            'sql_content': sql_content,
            'tables': tables or [],
            'transactions_valid': transactions_valid,
        }
    
    def get_extension(self, file_path: str) -> str:
        return self._archives.get(file_path, {}).get('extension', '')
    
    def is_valid_archive(self, file_path: str) -> bool:
        ext = self.get_extension(file_path)
        return ext in ['.sql', '.dump', '.gz', '.zip', '.tar', '.tgz']
    
    def is_sql_file(self, file_path: str) -> bool:
        return file_path.lower().endswith('.sql')
    
    def validate_sql_content(self, file_path: str, required_tables: list) -> Dict[str, Any]:
        archive = self._archives.get(file_path, {})
        content = archive.get('sql_content', '')
        tables = archive.get('tables', [])
        
        missing = [t for t in required_tables if t not in tables]
        return {
            'valid': len(missing) == 0,
            'missing_tables': missing,
            'checked_tables': required_tables,
        }
    
    def validate_transaction_integrity(self, file_path: str) -> Dict[str, Any]:
        archive = self._archives.get(file_path, {})
        valid = archive.get('transactions_valid', True)
        
        issues = [] if valid else ['Simulated transaction mismatch']
        return {
            'valid': valid,
            'issues': issues,
        }


def get_default_providers() -> tuple:
    """Get production providers for normal operation."""
    return (
        ProductionFileProvider(),
        ProductionChecksumProvider(),
        ProductionArchiveProvider(),
    )