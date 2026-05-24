"""
UUID utility functions.
"""
import uuid


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


def uuid_to_str(u: uuid.UUID) -> str:
    """Convert UUID object to string."""
    return str(u)


def str_to_uuid(s: str) -> uuid.UUID:
    """Convert string to UUID object."""
    return uuid.UUID(s) if s else uuid.uuid4()


def is_valid_uuid(s: str) -> bool:
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(s)
        return True
    except (ValueError, AttributeError):
        return False


def generate_short_code(length: int = 8) -> str:
    """Generate a short alphanumeric code."""
    return uuid.uuid4().hex[:length]


def generate_sequential_code(prefix: str = "", padding: int = 5, last_number: int = 0) -> str:
    """Generate a sequential code with prefix and padded number."""
    return f"{prefix}{str(last_number + 1).zfill(padding)}"
