"""The :class:`GroundingFinding` — a surfaced grounding problem.

A finding is raised for exactly the hallucination classifications
(``UNSUPPORTED`` / ``CONTRADICTED``). The validator enforces that contract so a
finding can never be minted for a supported requirement.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity.grounding_identity import GroundedRequirementId
from requirement_intelligence.grounding.models.enums import (
    HALLUCINATION_CLASSIFICATIONS,
    GroundingSeverity,
    SupportClassification,
)
from shared.contracts.base import Schema


class GroundingFinding(Schema):
    """A grounding problem worth surfacing — the framework's hallucination signal."""

    model_config = ConfigDict(alias_generator=to_camel)

    finding_id: str = Field(..., min_length=1, description="Identity of this finding.")
    requirement_id: GroundedRequirementId = Field(..., description="The offending requirement.")
    classification: SupportClassification = Field(..., description="Why it was flagged.")
    severity: GroundingSeverity = Field(..., description="Severity of the finding.")
    message: str = Field(..., min_length=1, description="Human-readable description.")

    @model_validator(mode="after")
    def _validate_finding(self) -> GroundingFinding:
        """A finding may only be raised for a hallucination classification."""
        if SupportClassification(self.classification) not in HALLUCINATION_CLASSIFICATIONS:
            raise ValueError(
                f"GroundingFinding '{self.finding_id}' has classification "
                f"'{self.classification}', which is not a hallucination class; findings are "
                f"raised only for UNSUPPORTED or CONTRADICTED."
            )
        return self
