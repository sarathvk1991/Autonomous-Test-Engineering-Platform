"""Identifier and time helpers shared across layers.

Small, dependency-free utilities. Keep this module pure — no I/O, no settings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_id() -> str:
    """Return a new globally-unique identifier as a string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
