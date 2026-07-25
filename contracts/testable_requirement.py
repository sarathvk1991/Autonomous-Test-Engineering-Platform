"""TestableRequirement — the Layer 1 -> Layer 2 boundary contract.

Per ADR-0034 (the six locked architectural properties) and ADR-0042 (the concrete
field specification this module implements exactly). This is the sole sanctioned
entry point anything outside Layer 1 may depend on; ``AnalysisResult`` stays
Layer-1-internal (ADR-0034 Decision, Recommendation 1).

``SourceRef`` is salvaged, unchanged in shape, from the removed
``requirement_intelligence/models/canonical_requirement.py`` (ADR-0035 item 2,
ADR-0042 Decision 4).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from contracts.id_generation import (
    compute_content_hash,
    generate_acceptance_criterion_id,
    generate_requirement_id,
    generate_risk_id,
)
from shared.contracts.base import Schema
from shared.enums.base import SourceSystem

#: The TestableRequirement contract version (ADR-0034 property 6, ADR-0042 Decision 6).
#: A future shape change is a version bump plus a passing compatibility test — never
#: a silent field addition or removal.
CONTRACT_VERSION = "1.0.0"


class Priority(StrEnum):
    """``TestableRequirement.priority`` — ADR-0042 Decision 1."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(StrEnum):
    """The three acceptance-criteria / risk domains — ADR-0042 Decision 1.

    Shared by :attr:`AcceptanceCriterion.category` and :attr:`Risk.category`: both
    fields name the same three-way domain axis.
    """

    FUNCTIONAL = "functional"
    SECURITY = "security"
    QUALITY = "quality"


class PolarityHint(StrEnum):
    """``AcceptanceCriterion.polarity_hints`` — ADR-0042 Decision 1.

    ``POSITIVE`` and ``NEGATIVE`` trace to the Layer 2 LLD's own scenario
    taxonomy; ``BOUNDARY`` is this contract's own refinement of the LLD's
    superseded boundary-data shape (ADR-0042's discrepancy note, Decision 1).
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"


class RequirementQualityGovernanceDecision(StrEnum):
    """``provenance.requirement_quality_governance_decision`` — ADR-0034 property 4.

    Deliberately two-valued, not the three-valued
    :class:`~requirement_intelligence.requirement_quality_governance.models.enums.QualityDecision`
    it is derived from: a ``FAIL`` run never reaches this envelope at all (the gate
    is enforced by non-emission, not by a representable-but-unused value), so this
    contract's own type cannot express ``FAIL`` in the first place.
    """

    PASS = "pass"  # noqa: S105 - a decision verdict, not a secret
    PASS_WITH_WARNINGS = "pass_with_warnings"  # noqa: S105 - a decision verdict, not a secret


class SourceRef(Schema):
    """Provenance pointer back to the originating record in a source system.

    Salvaged unchanged from the removed ``canonical_requirement.py`` (ADR-0042
    Decision 4) — same three fields, same shape, new home.
    """

    system: SourceSystem
    external_id: str
    url: str | None = None


class Risk(Schema):
    """A delivery/security/quality risk Layer 1 identified — never a scenario.

    Layer 1 emits risks; Layer 2 makes scenarios (ADR-0042 Decision 1, boundary
    note (a)).

    ``category`` is optional/nullable per ADR-0042 Decision 1's additive
    correction note (2026-07-25): the field was originally specified required,
    but ``AnalysisResult`` — the sole Layer 1 output this contract is populated
    from — carries no honest per-risk categorization signal. It emits ``null``
    in ``contract_version`` 1.0.0 until a future Layer 1 capability produces one.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    risk_id: str
    statement: str
    category: Category | None = None
    traces_to: tuple[SourceRef, ...] = Field(default_factory=tuple)


class AcceptanceCriterion(Schema):
    """One structured, individually identified, atomic acceptance criterion.

    Free-prose acceptance criteria are prohibited (ADR-0034 property 3); this is
    the structured unit Layer 2 scenarios (``SCN-*``) map to, never a requirement
    directly.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    criterion_id: str
    category: Category
    statement: str
    polarity_hints: tuple[PolarityHint, ...] = Field(default_factory=tuple)
    data_fields: tuple[str, ...] = Field(default_factory=tuple)
    traces_to: tuple[SourceRef, ...] = Field(default_factory=tuple)


class TestableRequirement(Schema):
    """One platform-assigned, content-addressed, individually traceable requirement.

    ``requirement_id`` and ``content_hash`` are never set directly — construct
    instances via :func:`build_testable_requirement`, which mints both
    deterministically per ADR-0042 Decisions 2 and 3.

    ``priority`` is optional/nullable per ADR-0042 Decision 1's additive
    correction note (2026-07-25): the field was originally specified required,
    but ``AnalysisResult`` — the sole Layer 1 output this contract is populated
    from — carries no honest per-requirement priority signal (the only priority
    signal anywhere in the pipeline is inbound ``SourceArtifact.priority``,
    formatted into the prompt, never emitted back). It emits ``null`` in
    ``contract_version`` 1.0.0 until a future Layer 1 capability produces one.
    """

    #: Not a pytest test class despite the name — silences pytest's Test* collector.
    __test__ = False

    model_config = ConfigDict(alias_generator=to_camel)

    requirement_id: str
    content_hash: str
    supersedes: str | None = None
    #: Unconstrained length. ADR-0042 cites the Gherkin Feature-name 70-char rule
    #: as this field's downstream consumer, but that limit is Layer 2/CP2's own
    #: concern (.gherkin-lintrc), never enforced here: Layer 1's title is the
    #: source of truth, over its full text, and REQ-* is content-addressed over
    #: that full text — truncating it here would risk hash collisions and would
    #: silently discard content Layer 2 needs to derive its own compliant name from.
    title: str
    component: str
    functional_tag: str
    narrative: str | None = None
    priority: Priority | None = None
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = Field(default_factory=tuple)
    risks: tuple[Risk, ...] = Field(default_factory=tuple)
    traces_to: tuple[SourceRef, ...] = Field(default_factory=tuple)


class TestableRequirementSetProvenance(Schema):
    """The ``provenance`` block of :class:`TestableRequirementSet` — ADR-0042 Decision 1."""

    __test__ = False

    model_config = ConfigDict(alias_generator=to_camel)

    prompt_id: str
    prompt_version: str
    prompt_sha256: str
    provider: str
    model: str
    requirement_quality_governance_decision: RequirementQualityGovernanceDecision
    governance_report_ref: str


class TestableRequirementSet(Schema):
    """The run-scoped envelope; the sole functional replacement for the removed
    ``RequirementPackage`` (ADR-0034, ADR-0035 item 3).

    One instance per run, containing every :class:`TestableRequirement` the run
    produced (ADR-0042 Decision 6 — not partitioned by component).
    """

    __test__ = False

    model_config = ConfigDict(alias_generator=to_camel)

    contract_version: str = CONTRACT_VERSION
    run_id: str
    generated_at: datetime
    provenance: TestableRequirementSetProvenance
    requirements: tuple[TestableRequirement, ...] = Field(default_factory=tuple)


@dataclass(frozen=True)
class AcceptanceCriterionInput:
    """Everything needed to build one :class:`AcceptanceCriterion` except its id.

    ``criterion_id`` is minted by :func:`build_testable_requirement` from the
    owning requirement's id and this input's stable ordinal position — never
    supplied here.
    """

    category: Category
    statement: str
    polarity_hints: tuple[PolarityHint, ...] = ()
    data_fields: tuple[str, ...] = ()
    traces_to: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class RiskInput:
    """Everything needed to build one :class:`Risk` except its id."""

    category: Category | None
    statement: str
    traces_to: tuple[SourceRef, ...] = ()


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_testable_requirement(
    *,
    title: str,
    component: str,
    functional_tag: str,
    priority: Priority | None,
    traces_to: Sequence[SourceRef],
    acceptance_criteria: Sequence[AcceptanceCriterionInput] = (),
    risks: Sequence[RiskInput] = (),
    narrative: str | None = None,
) -> TestableRequirement:
    """The sole constructor of a :class:`TestableRequirement`.

    Mints ``requirement_id`` (ADR-0042 Decision 2, over ``title`` + this
    requirement's own ``traces_to`` external ids), every ``AC-*``/``RSK-*`` id
    (Decision 2), and ``content_hash`` (Decision 3, over the requirement's
    canonical JSON excluding ``requirement_id``, ``content_hash``, and
    ``supersedes``) — never by the caller.
    """
    source_external_ids = [ref.external_id for ref in traces_to]
    requirement_id = generate_requirement_id(title, source_external_ids)

    built_criteria = tuple(
        AcceptanceCriterion(
            criterion_id=generate_acceptance_criterion_id(requirement_id, ordinal),
            category=criterion.category,
            statement=criterion.statement,
            polarity_hints=criterion.polarity_hints,
            data_fields=criterion.data_fields,
            traces_to=criterion.traces_to,
        )
        for ordinal, criterion in enumerate(acceptance_criteria, start=1)
    )
    built_risks = tuple(
        Risk(
            risk_id=generate_risk_id(
                risk.statement, [ref.external_id for ref in risk.traces_to]
            ),
            statement=risk.statement,
            category=risk.category,
            traces_to=risk.traces_to,
        )
        for risk in risks
    )

    content_fields = {
        "title": title,
        "component": component,
        "functionalTag": functional_tag,
        "narrative": narrative,
        "priority": priority.value if priority is not None else None,
        "acceptanceCriteria": [
            ac.model_dump(mode="json", by_alias=True) for ac in built_criteria
        ],
        "risks": [risk.model_dump(mode="json", by_alias=True) for risk in built_risks],
        "tracesTo": [ref.model_dump(mode="json", by_alias=True) for ref in traces_to],
    }
    content_hash = compute_content_hash(_canonical_json(content_fields))

    return TestableRequirement(
        requirement_id=requirement_id,
        content_hash=content_hash,
        supersedes=None,
        title=title,
        component=component,
        functional_tag=functional_tag,
        narrative=narrative,
        priority=priority,
        acceptance_criteria=built_criteria,
        risks=built_risks,
        traces_to=tuple(traces_to),
    )


__all__ = [
    "CONTRACT_VERSION",
    "AcceptanceCriterion",
    "AcceptanceCriterionInput",
    "Category",
    "PolarityHint",
    "Priority",
    "RequirementQualityGovernanceDecision",
    "Risk",
    "RiskInput",
    "SourceRef",
    "TestableRequirement",
    "TestableRequirementSet",
    "TestableRequirementSetProvenance",
    "build_testable_requirement",
]
