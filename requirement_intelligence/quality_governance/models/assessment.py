"""The :class:`QualityAssessment` — the per-run governance aggregate.

``QualityAssessment`` is the governance body for one Requirement Intelligence run:
the decision, every governance finding, the headline summary, and the governing
policy identity/version. It is the Quality Governance analogue of
``GroundingAssessment``.

The validators enforce **cross-referential integrity and explainability only** — the
summary agrees with the findings it summarises, and the recorded decision is
explainable by those findings (ADR-0017 Recommendation 3). No score is computed, no
rule is evaluated, and no decision is derived here.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityAssessmentId,
    QualityAssessmentVersion,
    QualityGovernanceVersion,
    QualityPolicyId,
    QualityPolicyVersion,
)
from requirement_intelligence.quality_governance.models.enums import (
    QualityDecision,
    QualitySeverity,
)
from requirement_intelligence.quality_governance.models.findings import QualityFinding
from requirement_intelligence.quality_governance.models.summary import QualitySummary
from shared.contracts.base import Schema

#: Version of the ``QualityAssessment`` **schema**. Independent of the framework,
#: policy, and result-contract versions; advances additively under the golden
#: re-baseline procedure.
QUALITY_ASSESSMENT_VERSION = QualityAssessmentVersion(1, 0, 0)


class QualityAssessment(Schema):
    """The complete quality governance assessment for one Requirement Intelligence run."""

    model_config = ConfigDict(alias_generator=to_camel)

    assessment_id: QualityAssessmentId = Field(..., description="Deterministic assessment id.")
    analysis_id: str = Field(..., min_length=1, description="The analysis this governs.")
    execution_id: str = Field(..., min_length=1, description="The AI invocation this governs.")

    decision: QualityDecision = Field(..., description="The governed release decision.")
    findings: tuple[QualityFinding, ...] = Field(
        default=(), description="Every governance finding raised for this run."
    )
    summary: QualitySummary = Field(..., description="The headline governance summary.")

    policy_id: QualityPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: QualityPolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: QualityGovernanceVersion = Field(...)
    assessment_version: QualityAssessmentVersion = Field(
        default=QUALITY_ASSESSMENT_VERSION,
        description="Version of the QualityAssessment schema.",
    )

    @model_validator(mode="after")
    def _validate_assessment(self) -> QualityAssessment:
        """Summary agrees with findings, and the decision is explainable by them.

        A consistency/explainability invariant only — no value is computed and no
        decision is derived. It guarantees the recorded decision can be audited from
        the assessment alone (ADR-0017 Recommendation 3).
        """
        if self.summary.decision != self.decision:
            raise ValueError(
                f"Summary decision '{self.summary.decision}' does not match assessment "
                f"decision '{self.decision}'."
            )
        if self.summary.policy_id != self.policy_id or self.summary.policy_version != (
            self.policy_version
        ):
            raise ValueError("Summary policy identity/version does not match the assessment's.")

        warnings = sum(
            1 for f in self.findings if QualitySeverity(f.severity) is QualitySeverity.WARNING
        )
        failures = sum(
            1 for f in self.findings if QualitySeverity(f.severity) is QualitySeverity.FAILURE
        )
        if self.summary.total_findings != len(self.findings):
            raise ValueError(
                f"Summary total_findings {self.summary.total_findings} does not match "
                f"{len(self.findings)} findings."
            )
        if self.summary.warning_count != warnings or self.summary.failure_count != failures:
            raise ValueError(
                "Summary warning/failure counts do not match the findings' severities: "
                f"warnings={warnings}, failures={failures}."
            )

        decision = QualityDecision(self.decision)
        if decision is QualityDecision.FAIL and failures == 0:
            raise ValueError("A FAIL decision must be explained by at least one FAILURE finding.")
        if decision is QualityDecision.PASS and (warnings or failures):
            raise ValueError("A PASS decision cannot carry WARNING or FAILURE findings.")
        if decision is QualityDecision.PASS_WITH_WARNINGS and (warnings == 0 or failures):
            raise ValueError(
                "A PASS_WITH_WARNINGS decision requires WARNING findings and no FAILURE findings."
            )
        return self
