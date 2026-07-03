"""Validation Profiles — governed, immutable rule-selection identities.

This package owns the **orchestration-layer** Validation Profiles: named,
governed selections of validation layers whose implemented rules a run executes.
They are distinct from the Response Validator's internal
:class:`~requirement_intelligence.validation.response.validation_profile.ValidationProfile`
(run-policy identity); these definitions drive *which rules the Validation Factory
registers*. Profiles are orchestration only — rules never know about them, and
ordering remains governed exclusively by ``LAYER_ORDER``.

The :class:`ValidationProfileRegistry` is the sole owner of the definitions; it
constructs nothing and executes nothing.
"""

from requirement_intelligence.validation.profiles.validation_profile_definition import (
    ValidationProfileDefinition,
)
from requirement_intelligence.validation.profiles.validation_profile_registry import (
    CONTENT_REVIEW,
    DEFAULT,
    SCHEMA_ONLY,
    STRICT,
    SYNTAX_ONLY,
    TRANSPORT_ONLY,
    UnknownValidationProfileError,
    ValidationProfileRegistry,
)

__all__ = [
    "CONTENT_REVIEW",
    "DEFAULT",
    "SCHEMA_ONLY",
    "STRICT",
    "SYNTAX_ONLY",
    "TRANSPORT_ONLY",
    "UnknownValidationProfileError",
    "ValidationProfileDefinition",
    "ValidationProfileRegistry",
]
