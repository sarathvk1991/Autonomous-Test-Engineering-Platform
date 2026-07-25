"""Layer 1's TestableRequirementSet emitter (ADR-0032 carve-out 1).

Re-exports :mod:`requirement_intelligence.testable_requirement.emitter`'s public
surface so callers can import from the package root.
"""

from __future__ import annotations

from requirement_intelligence.testable_requirement.emitter import (
    TestableRequirementEmissionError,
    emit_testable_requirement_set,
    gate_permits_emission,
)

__all__ = [
    "TestableRequirementEmissionError",
    "emit_testable_requirement_set",
    "gate_permits_emission",
]
