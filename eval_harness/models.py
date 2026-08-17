"""ADR-0051's own data shapes -- the eval harness's curated-check result
(``PropertyCheckResult``), one case's aggregate (``CaseResult``), one
generator's scored run (``EvalScore``), and the regression-gate verdict
(``RegressionGateResult``).

Deliberately NOT a new detection vocabulary (ADR-0051 D1, the reframe):
these shapes carry the OUTCOME of checks this package composes from
existing, largely-already-proven detection logic (CP5-class structural
checks, CAP-088's `CompletenessReport`/`BindingCompletenessReport`) -- they
are the curation/scoring/regression-gating scaffolding around that
detection, not a new way of recognizing a bad artifact.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.llm.generation_identity import GenerationIdentity
from shared.contracts.base import Schema


class PropertyCheckOutcome(StrEnum):
    """One deterministic property check's own verdict on one generated
    artifact. ``NOT_APPLICABLE`` (not ``PASSED``) is a first-class outcome,
    not a shortcut -- a check that has nothing to evaluate for this case
    (e.g. no Cucumber annotation to check an import against, or no
    page-object interface was expected) must never silently count as
    evidence of quality; it is excluded from the pass-rate denominator
    entirely (:mod:`.scoring`), the same "unmeasured is not the same as
    zero-cost-verified" discipline `TokenUsageTotals` already established
    for the cache-hit bucket.
    """

    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class PropertyCheckResult(Schema):
    """One named check's outcome against one generated artifact."""

    model_config = ConfigDict(alias_generator=to_camel)

    check_name: str = Field(..., min_length=1)
    outcome: PropertyCheckOutcome
    reason: str = Field(default="")


class CaseResult(Schema):
    """One curated eval case's full set of property-check outcomes."""

    model_config = ConfigDict(alias_generator=to_camel)

    case_id: str = Field(..., min_length=1)
    check_results: tuple[PropertyCheckResult, ...] = Field(..., min_length=1)

    @property
    def passed(self) -> bool:
        """True iff no applicable check FAILED -- ``NOT_APPLICABLE`` checks
        never block a case from passing."""
        return not any(
            result.outcome == PropertyCheckOutcome.FAILED for result in self.check_results
        )


class EvalScore(Schema):
    """One generator's scored run against one curated eval set, at one
    :class:`GenerationIdentity` -- the unit this package's regression gate
    (:mod:`.baseline_store`) compares over time.

    ``total_checks_applicable``/``total_checks_passed``/``pass_rate`` are
    always derived from ``case_results`` (the ``_score_is_consistent``
    validator enforces it, mirroring
    `BindingCompletenessReport._counts_are_consistent`'s own discipline) --
    never independently supplied and possibly wrong.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    generator_id: str = Field(..., min_length=1)
    eval_set_version: str = Field(..., min_length=1)
    identity: GenerationIdentity
    case_results: tuple[CaseResult, ...] = Field(..., min_length=1)
    total_checks_applicable: int = Field(..., ge=0)
    total_checks_passed: int = Field(..., ge=0)
    pass_rate: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _score_is_consistent(self) -> EvalScore:
        applicable = [
            result
            for case in self.case_results
            for result in case.check_results
            if result.outcome != PropertyCheckOutcome.NOT_APPLICABLE
        ]
        passed = [result for result in applicable if result.outcome == PropertyCheckOutcome.PASSED]
        if len(applicable) != self.total_checks_applicable:
            raise ValueError(
                "total_checks_applicable must equal the number of non-NOT_APPLICABLE "
                f"check results across case_results (got {self.total_checks_applicable}, "
                f"computed {len(applicable)})."
            )
        if len(passed) != self.total_checks_passed:
            raise ValueError(
                "total_checks_passed must equal the number of PASSED check results "
                f"across case_results (got {self.total_checks_passed}, computed {len(passed)})."
            )
        expected_rate = (len(passed) / len(applicable)) if applicable else 1.0
        if abs(expected_rate - self.pass_rate) > 1e-9:
            raise ValueError(
                f"pass_rate ({self.pass_rate}) does not match "
                f"total_checks_passed/total_checks_applicable ({expected_rate})."
            )
        return self


class RegressionGateOutcome(StrEnum):
    """The regression gate's own verdict -- always relative to a stored
    baseline, never an absolute score threshold (ADR-0051 D2: "avoiding the
    pass-bias meaning-check trap" a hardcoded numeric bar risks)."""

    ESTABLISHED_BASELINE = "established_baseline"
    PASSED = "passed"
    REGRESSED = "regressed"


class RegressionGateResult(Schema):
    """The regression gate's verdict for one candidate :class:`EvalScore`
    against a generator's stored baseline (:mod:`.baseline_store`)."""

    model_config = ConfigDict(alias_generator=to_camel)

    outcome: RegressionGateOutcome
    candidate_pass_rate: float = Field(..., ge=0.0, le=1.0)
    baseline_pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str = Field(default="")


__all__ = [
    "CaseResult",
    "EvalScore",
    "PropertyCheckOutcome",
    "PropertyCheckResult",
    "RegressionGateOutcome",
    "RegressionGateResult",
]
