"""Contract tests for TestableRequirement / TestableRequirementSet (ADR-0034, ADR-0042).

Covers: the round-trip guarantee, the checked-in JSON Schema compatibility gate
(ADR-0034 property 6 / ADR-0042 Decision 6), ADR-0042's exact field shapes, the
frozen/extra-forbid discipline inherited from ``shared.contracts.base.Schema``,
``supersedes`` emitting ``null`` in v1.0.0 (ADR-0042 Decision 5), and
``content_hash``'s exclusion set (ADR-0042 Decision 3).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.testable_requirement import (
    CONTRACT_VERSION,
    AcceptanceCriterionInput,
    Category,
    PolarityHint,
    Priority,
    RequirementQualityGovernanceDecision,
    RiskInput,
    SourceRef,
    TestableRequirementSet,
    TestableRequirementSetProvenance,
    build_risk,
    build_testable_requirement,
)
from shared.enums.base import SourceSystem

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "schemas"
    / "testable_requirement_set.schema.json"
)

_REF = SourceRef(system=SourceSystem.JIRA, external_id="PROJ-1", url="https://example.com/PROJ-1")


def _make_requirement_set() -> TestableRequirementSet:
    requirement = build_testable_requirement(
        title="Account must lock after 5 failed attempts",
        component="auth",
        functional_tag="@login",
        priority=Priority.HIGH,
        traces_to=[_REF],
        acceptance_criteria=[
            AcceptanceCriterionInput(
                category=Category.SECURITY,
                statement="Locks after 5 consecutive failed attempts",
                polarity_hints=(PolarityHint.NEGATIVE,),
            ),
        ],
    )
    risk = build_risk(
        RiskInput(category=Category.SECURITY, statement="Brute force risk", traces_to=(_REF,))
    )
    return TestableRequirementSet(
        run_id="run-1",
        generated_at=datetime(2026, 7, 25, tzinfo=UTC),
        provenance=TestableRequirementSetProvenance(
            prompt_id="requirement-analysis",
            prompt_version="1.0.0",
            prompt_sha256="a" * 64,
            provider="gemini",
            model="gemini-3.1-flash-lite",
            requirement_quality_governance_decision=RequirementQualityGovernanceDecision.PASS,
            governance_report_ref="quality_governance_report.md",
        ),
        requirements=[requirement],
        risks=[risk],
    )


@pytest.mark.unit
class TestRoundTrip:
    def test_serialize_reload_equal(self) -> None:
        original = _make_requirement_set()
        reloaded = TestableRequirementSet.model_validate_json(original.model_dump_json())
        assert reloaded == original

    def test_round_trips_through_plain_dict(self) -> None:
        original = _make_requirement_set()
        dumped = original.model_dump(mode="json", by_alias=True)
        reloaded = TestableRequirementSet.model_validate(dumped)
        assert reloaded == original


@pytest.mark.unit
class TestCompatibility:
    """ADR-0034 property 6 / ADR-0042 Decision 6: a field added, removed, or
    retyped without a version bump must fail this test."""

    def test_checked_in_schema_matches_the_live_model(self) -> None:
        live_schema = TestableRequirementSet.model_json_schema()
        on_disk = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        assert live_schema == on_disk, (
            "contracts/schemas/testable_requirement_set.schema.json is stale — "
            "regenerate it and bump contract_version if this is an intentional "
            "shape change."
        )

    def test_contract_version_is_1_0_0(self) -> None:
        assert CONTRACT_VERSION == "1.0.0"
        assert TestableRequirementSet.model_fields["contract_version"].default == "1.0.0"


@pytest.mark.unit
class TestFrozenAndStrict:
    def test_requirement_set_is_frozen(self) -> None:
        instance = _make_requirement_set()
        with pytest.raises(ValidationError):
            instance.run_id = "run-2"  # type: ignore[misc]

    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SourceRef(
                system=SourceSystem.JIRA,
                external_id="PROJ-1",
                url=None,
                unexpected="nope",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestSourceRefSalvage:
    """ADR-0042 Decision 4: salvaged as-is — system / external_id / url, nothing else."""

    def test_field_set(self) -> None:
        assert set(SourceRef.model_fields) == {"system", "external_id", "url"}

    def test_url_optional(self) -> None:
        ref = SourceRef(system=SourceSystem.OWASP_ZAP, external_id="zap-alert-10202")
        assert ref.url is None

    def test_all_three_source_systems_representable(self) -> None:
        for system in (SourceSystem.JIRA, SourceSystem.SONARQUBE, SourceSystem.OWASP_ZAP):
            ref = SourceRef(system=system, external_id="x")
            assert ref.system == system

    def test_serializes_camel_case_consistent_with_the_rest_of_the_document(self) -> None:
        """Found while sanity-checking the emitter against a real run: SourceRef
        originally had no alias generator, so tracesTo[] entries serialized
        external_id in snake_case while every other field in the same document
        is camelCase. SourceRef now carries the same alias_generator as its
        siblings."""
        ref = SourceRef(system=SourceSystem.JIRA, external_id="PROJ-1")
        dumped = ref.model_dump(mode="json", by_alias=True)
        assert dumped == {"system": "jira", "externalId": "PROJ-1", "url": None}
        assert "external_id" not in dumped


@pytest.mark.unit
class TestSupersedes:
    """ADR-0042 Decision 5: the field exists and emits null in v1.0.0."""

    def test_supersedes_is_none(self) -> None:
        requirement = build_testable_requirement(
            title="Some requirement",
            component="auth",
            functional_tag="@auth",
            priority=Priority.MEDIUM,
            traces_to=[_REF],
        )
        assert requirement.supersedes is None

    def test_supersedes_serializes_to_null(self) -> None:
        requirement = build_testable_requirement(
            title="Some requirement",
            component="auth",
            functional_tag="@auth",
            priority=Priority.MEDIUM,
            traces_to=[_REF],
        )
        dumped = requirement.model_dump(mode="json", by_alias=True)
        assert dumped["supersedes"] is None


@pytest.mark.unit
class TestOptionalCorrectionNote:
    """ADR-0042 Decision 1's additive correction note (2026-07-25): priority and
    Risk.category were specified required with no honest AnalysisResult signal
    to populate them, so both are corrected to optional/nullable in v1.0.0."""

    def test_priority_may_be_none(self) -> None:
        requirement = build_testable_requirement(
            title="Some requirement",
            component="auth",
            functional_tag="@auth",
            priority=None,
            traces_to=[_REF],
        )
        assert requirement.priority is None

    def test_priority_none_serializes_to_null(self) -> None:
        requirement = build_testable_requirement(
            title="Some requirement",
            component="auth",
            functional_tag="@auth",
            priority=None,
            traces_to=[_REF],
        )
        dumped = requirement.model_dump(mode="json", by_alias=True)
        assert dumped["priority"] is None

    def test_risk_category_may_be_none(self) -> None:
        risk = build_risk(
            RiskInput(category=None, statement="Unclassified risk", traces_to=(_REF,))
        )
        assert risk.category is None

    def test_risk_category_none_serializes_to_null(self) -> None:
        risk = build_risk(
            RiskInput(category=None, statement="Unclassified risk", traces_to=(_REF,))
        )
        dumped = risk.model_dump(mode="json", by_alias=True)
        assert dumped["category"] is None

    def test_acceptance_criterion_traces_to_is_always_empty(self) -> None:
        """ADR-0042 Decision 1's third correction note (2026-07-25):
        AcceptanceCriterion.traces_to has no honest source in contract_version
        1.0.0 and is always empty — AcceptanceCriterionInput offers no parameter
        that could set it otherwise."""
        requirement = build_testable_requirement(
            title="Some requirement",
            component="auth",
            functional_tag="@auth",
            priority=Priority.MEDIUM,
            traces_to=[_REF],
            acceptance_criteria=[
                AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="y")
            ],
        )
        assert requirement.acceptance_criteria[0].traces_to == ()

    def test_requirement_traces_to_is_unaffected(self) -> None:
        """Requirement-level provenance IS honestly available and is unaffected
        by the AcceptanceCriterion.traces_to correction."""
        requirement = build_testable_requirement(
            title="Some requirement",
            component="auth",
            functional_tag="@auth",
            priority=Priority.MEDIUM,
            traces_to=[_REF],
        )
        assert requirement.traces_to == (_REF,)


@pytest.mark.unit
class TestContentHash:
    def test_identical_input_yields_identical_hash(self) -> None:
        kwargs = dict(
            title="Account must lock after 5 failed attempts",
            component="auth",
            functional_tag="@login",
            priority=Priority.HIGH,
            traces_to=[_REF],
        )
        a = build_testable_requirement(**kwargs)  # type: ignore[arg-type]
        b = build_testable_requirement(**kwargs)  # type: ignore[arg-type]
        assert a.content_hash == b.content_hash
        assert a.requirement_id == b.requirement_id

    def test_content_change_changes_hash_but_not_excluded_fields_alone(self) -> None:
        base = build_testable_requirement(
            title="Account must lock after 5 failed attempts",
            component="auth",
            functional_tag="@login",
            priority=Priority.HIGH,
            traces_to=[_REF],
        )
        changed_narrative = build_testable_requirement(
            title="Account must lock after 5 failed attempts",
            component="auth",
            functional_tag="@login",
            priority=Priority.HIGH,
            traces_to=[_REF],
            narrative="Extra business context",
        )
        assert base.content_hash != changed_narrative.content_hash

    def test_content_hash_is_stable_regardless_of_supersedes(self) -> None:
        # supersedes is always None from build_testable_requirement in v1.0.0
        # (Decision 5); content_hash must not vary if a caller later attaches
        # a supersedes value via model_copy — it is excluded from the hash input.
        base = build_testable_requirement(
            title="Account must lock after 5 failed attempts",
            component="auth",
            functional_tag="@login",
            priority=Priority.HIGH,
            traces_to=[_REF],
        )
        superseding = base.model_copy(update={"supersedes": "REQ-deadbeef"})
        assert base.content_hash == superseding.content_hash


@pytest.mark.unit
class TestFieldShapes:
    """Spot-check ADR-0042 Decision 1's field tables exactly — no extra fields,
    none missing."""

    def test_testable_requirement_set_fields(self) -> None:
        expected = {
            "contract_version",
            "run_id",
            "generated_at",
            "provenance",
            "requirements",
            "risks",
        }
        assert set(TestableRequirementSet.model_fields) == expected

    def test_testable_requirement_provenance_fields(self) -> None:
        expected = {
            "prompt_id",
            "prompt_version",
            "prompt_sha256",
            "provider",
            "model",
            "requirement_quality_governance_decision",
            "governance_report_ref",
        }
        assert set(TestableRequirementSetProvenance.model_fields) == expected

    def test_testable_requirement_fields(self) -> None:
        requirement = build_testable_requirement(
            title="X",
            component="auth",
            functional_tag="@x",
            priority=Priority.LOW,
            traces_to=[_REF],
        )
        expected = {
            "requirement_id",
            "content_hash",
            "supersedes",
            "title",
            "component",
            "functional_tag",
            "narrative",
            "priority",
            "acceptance_criteria",
            "risks",
            "traces_to",
        }
        assert set(type(requirement).model_fields) == expected

    def test_acceptance_criterion_fields(self) -> None:
        requirement = build_testable_requirement(
            title="X",
            component="auth",
            functional_tag="@x",
            priority=Priority.LOW,
            traces_to=[_REF],
            acceptance_criteria=[
                AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="y")
            ],
        )
        expected = {
            "criterion_id",
            "category",
            "statement",
            "polarity_hints",
            "data_fields",
            "traces_to",
        }
        assert set(type(requirement.acceptance_criteria[0]).model_fields) == expected

    def test_risk_fields(self) -> None:
        risk = build_risk(RiskInput(category=Category.QUALITY, statement="y"))
        expected = {"risk_id", "statement", "category", "traces_to"}
        assert set(type(risk).model_fields) == expected

    def test_testable_requirement_risks_field_is_always_empty(self) -> None:
        """TestableRequirement.risks stays in the schema, reserved, per ADR-0042
        Decision 1's structural correction note (2026-07-25) — risks live on
        TestableRequirementSet now."""
        requirement = build_testable_requirement(
            title="X",
            component="auth",
            functional_tag="@x",
            priority=Priority.LOW,
            traces_to=[_REF],
        )
        assert requirement.risks == ()

    def test_requirement_set_risks_are_populated(self) -> None:
        risk = build_risk(RiskInput(category=Category.QUALITY, statement="y", traces_to=(_REF,)))
        requirement_set = TestableRequirementSet(
            run_id="run-1",
            generated_at=datetime(2026, 7, 25, tzinfo=UTC),
            provenance=TestableRequirementSetProvenance(
                prompt_id="requirement-analysis",
                prompt_version="1.0.0",
                prompt_sha256="a" * 64,
                provider="gemini",
                model="gemini-3.1-flash-lite",
                requirement_quality_governance_decision=RequirementQualityGovernanceDecision.PASS,
                governance_report_ref="quality_governance_report.md",
            ),
            requirements=[],
            risks=[risk],
        )
        assert requirement_set.risks == (risk,)

    def test_title_over_70_chars_accepted_unmodified(self) -> None:
        """title has no length constraint at Layer 1: the .gherkin-lintrc 70-char
        Feature-name rule ADR-0042 cites is Layer 2/CP2's own downstream concern,
        never enforced on this contract. Layer 1 emits the full text; a longer
        title is neither rejected nor truncated."""
        long_title = "x" * 140
        requirement = build_testable_requirement(
            title=long_title,
            component="auth",
            functional_tag="@x",
            priority=Priority.LOW,
            traces_to=[_REF],
        )
        assert requirement.title == long_title

    def test_requirement_id_is_stable_and_unique_over_full_title_beyond_70_chars(self) -> None:
        """REQ-* is content-addressed over the full title, not a truncated prefix
        — two titles that only differ after char 70 must not collide."""
        prefix = "x" * 70
        a = build_testable_requirement(
            title=prefix + "-alpha",
            component="auth",
            functional_tag="@x",
            priority=Priority.LOW,
            traces_to=[_REF],
        )
        b = build_testable_requirement(
            title=prefix + "-beta",
            component="auth",
            functional_tag="@x",
            priority=Priority.LOW,
            traces_to=[_REF],
        )
        assert a.requirement_id != b.requirement_id
