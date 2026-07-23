"""Common system utilities and helpers."""

import uuid
from datetime import datetime


def generate_uuid() -> str:
    """Generate a string representation of UUID4."""
    return str(uuid.uuid4())


def current_utc_timestamp() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()
