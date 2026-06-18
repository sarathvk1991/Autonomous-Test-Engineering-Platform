"""CP1 Validation Engine.

CP1 ("Control Point 1") is the first quality gate of the platform: it decides
whether the consolidated/classified/analyzed requirement set is good enough to
proceed to the Feature Engineering Layer. Encapsulates the CP1 rule set and
produces a pass/fail verdict with findings. Logic deferred.
"""

from __future__ import annotations

from requirement_intelligence.models.canonical_requirement import CanonicalRequirement
from shared.contracts.base import Schema
from shared.enums.base import ValidationVerdict


class CP1Finding(Schema):
    """A single issue raised by the CP1 gate."""

    requirement_id: str
    rule: str
    message: str
    verdict: ValidationVerdict


class CP1Result(Schema):
    """Aggregate outcome of a CP1 validation run."""

    verdict: ValidationVerdict
    findings: list[CP1Finding] = []


class CP1Validator:
    """Evaluates the CP1 quality gate over a requirement set."""

    def validate(self, requirements: list[CanonicalRequirement]) -> CP1Result:
        """Run the CP1 rule set and return the verdict + findings."""
        raise NotImplementedError
