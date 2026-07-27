"""Layer 1's TestableRequirementSet emitter (ADR-0032 carve-out 1).

Maps the existing ``AnalysisResult`` (+ the ``EngineeringContext`` it reasoned
over, + the primary ``ConsolidatedArtifact``) into the ``TestableRequirementSet``
boundary contract (ADR-0034, ADR-0042). This is ADDITIVE: it introduces no
judgement, modifies no existing runtime model, and changes no existing Execution
Package artifact. ``AnalysisResult`` stays exactly what it is today (ADR-0034
Decision) — this module only reads it.

Field-mapping decisions and gaps, all investigated and resolved against ADR-0042
before this module was written (see the additive correction notes in
``docs/adr/0042-testablerequirement-field-specification.md`` Decision 1):

* ``priority`` and ``Risk.category`` have no honest per-item signal in
  ``AnalysisResult`` — always ``None``.
* ``AcceptanceCriterion.traces_to`` has no honest per-criterion signal — always
  empty; ``TestableRequirement.traces_to`` carries the honest group-level
  provenance instead.
* ``risks`` live on ``TestableRequirementSet``, not per-requirement — Layer 1's
  risks are a flat, run-level list with no per-requirement attribution.
* ``title`` is unconstrained — the .gherkin-lintrc 70-char rule ADR-0042 cites is
  Layer 2/CP2's own downstream concern, never enforced here.
* One ``TestableRequirement`` is emitted per generated requirement statement,
  carrying exactly one ``AcceptanceCriterion`` whose ``statement`` is that same
  text: the raw response gives Layer 1 no separate criteria structure to draw
  on, so the requirement's own statement is its own sole (currently
  unelaborated) criterion — not fabricated content, the same content under its
  two structural roles.

``traces_to`` scope (corrected against CAP-076D facts, investigated before this
module was written). ``AnalysisResult.source_consolidated_id`` is a
comma-joined **echo** of every contributing ``ConsolidatedArtifact``'s id under
the active multi-source policy (``requirement_analysis_service.py``, empirically
confirmed: 10 groups on a real run, not 1) — never parsed here, since splitting
a joined string is fragile and ``EngineeringContext`` already exposes the same
set structurally. ``traces_to`` is built from
``EngineeringContext.evidence.{functional,security,quality}_artifacts`` — the
orchestrator's own flattened, order-fixed evidence across every contributing
group, i.e. what the reasoner actually saw. This is deliberately **broader**
than ``consolidated_artifact.json`` (``ExecutionData.selected`` /
``orchestration.primary_group``), which persists only the single highest-ranked
group: selection (one winner, for artifact generation) and provenance (every
group the reasoning spanned) answer different questions, and ``component`` /
``functional_tag`` still come from the primary group alone (ADR-0042 Decision
1(b) — one requirement set, one path). Deduplicated by ``(system, external_id)``
and sorted by that same key before conversion to ``SourceRef`` — the
orchestrator's own tuple order is already fixed, but sorting here makes
``traces_to`` (and therefore ``content_hash`` and ``REQ-*``) reproducible from
the evidence's own content alone, independent of any upstream ordering
behaviour, per ADR-0036's idempotency requirement.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    RequirementQualityGovernanceDecision,
    RiskInput,
    SourceRef,
    TestableRequirement,
    TestableRequirementSet,
    TestableRequirementSetProvenance,
    build_risk,
    build_testable_requirement,
)
from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.source_artifact import SourceArtifact
from requirement_intelligence.prompts.requirement_prompt_builder import RUNTIME_PROMPT_ID
from requirement_intelligence.requirement_quality_governance.models.result import (
    QualityGovernanceResult,
)
from shared.prompts.framework.prompt_registry import PromptRegistry

#: The response arrays that hold generated requirements, mapped to their
#: AcceptanceCriterion category, in canonical domain order. Mirrors
#: Enhancement's and Grounding's own independent extraction of the same shape
#: (module docstrings of both name the "duplicate rather than couple"
#: precedent, ADR-0015 §C / ADR-0016 §D6) — this emitter follows the same
#: precedent rather than importing either subsystem's extraction logic.
_REQUIREMENT_ARRAYS: tuple[tuple[str, Category], ...] = (
    ("functional_requirements", Category.FUNCTIONAL),
    ("security_requirements", Category.SECURITY),
    ("quality_requirements", Category.QUALITY),
)

#: The response array that holds identified risks — a flat list of strings with
#: no per-requirement attribution (ADR-0042 Decision 1's structural correction).
_RISK_ARRAY_KEY = "risks"

#: Decisions that permit a TestableRequirementSet to cross the Layer 1 -> Layer 2
#: boundary (ADR-0034 property 4). A FAIL run reaches neither this module nor
#: any caller of it — the CLI only calls emit_testable_requirement_set() when
#: this predicate already holds; see gate_permits_emission().
_PERMITTED_DECISIONS = frozenset({"pass", "pass_with_warnings"})

_TAG_STRIP_RE = re.compile(r"[^a-z0-9]+")


class TestableRequirementEmissionError(ValueError):
    """Raised when a TestableRequirementSet cannot be honestly emitted."""

    #: Not a pytest test class despite the name — silences pytest's Test* collector.
    __test__ = False


def gate_permits_emission(governance_result: QualityGovernanceResult) -> bool:
    """Whether *governance_result* permits crossing the Layer 1 -> Layer 2 boundary.

    ADR-0034 property 4: only ``PASS``/``PASS_WITH_WARNINGS`` runs emit a
    ``TestableRequirementSet`` at all; a ``FAIL`` run emits nothing.
    """
    return governance_result.assessment.decision in _PERMITTED_DECISIONS


def _response_object(analysis_result: AnalysisResult) -> dict[str, Any]:
    """Parse the strict-JSON response body, or reject extraction.

    Mirrors the Requirement Enhancement engine's own equivalent extraction
    helper — independently, per the same "duplicate rather than couple"
    precedent (see the module docstring).
    """
    text = analysis_result.llm_response.generated_text
    try:
        body = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise TestableRequirementEmissionError(
            "AI response body is not valid JSON; cannot emit a TestableRequirementSet."
        ) from exc
    if not isinstance(body, dict):
        raise TestableRequirementEmissionError(
            "AI response body is not a JSON object; cannot emit a TestableRequirementSet."
        )
    return body


def _source_refs(engineering_context: EngineeringContext) -> tuple[SourceRef, ...]:
    """The run-level SourceRef set: every SourceArtifact the reasoner actually
    saw, across every contributing ConsolidatedArtifact group — not just the
    primary one (see the module docstring's ``traces_to`` scope note).

    Deduplicated and sorted by ``(source_system, source_record_id)`` for
    reproducibility, independent of the orchestrator's own tuple ordering.
    """
    evidence = engineering_context.evidence
    artifacts: tuple[SourceArtifact, ...] = (
        *evidence.functional_artifacts,
        *evidence.security_artifacts,
        *evidence.quality_artifacts,
    )
    deduplicated: dict[tuple[str, str], SourceArtifact] = {
        (str(artifact.source_system), artifact.source_record_id): artifact for artifact in artifacts
    }
    return tuple(
        SourceRef(
            system=artifact.source_system,
            external_id=artifact.source_record_id,
            url=artifact.url,
        )
        for _key, artifact in sorted(deduplicated.items(), key=lambda item: item[0])
    )


def _functional_tag(component: str) -> str:
    """A deterministic, platform-supplied tag derived from *component*.

    ADR-0042: "``functional_tag`` | string, e.g. ``\"@login\"``, platform-supplied."
    No LLM signal is used — the tag is a pure function of the group's own
    ``module`` name.
    """
    slug = _TAG_STRIP_RE.sub("", component.lower())
    return f"@{slug}" if slug else "@unclassified"


def _texts(body: dict[str, Any], key: str) -> list[str]:
    values = body.get(key, [])
    if not isinstance(values, list):
        raise TestableRequirementEmissionError(
            f"Response field '{key}' is not a list; cannot emit a TestableRequirementSet."
        )
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def emit_testable_requirement_set(
    *,
    run_id: str,
    analysis_result: AnalysisResult,
    engineering_context: EngineeringContext,
    consolidated_artifact: ConsolidatedArtifact,
    governance_result: QualityGovernanceResult,
    prompt_registry: PromptRegistry,
    generated_at: datetime | None = None,
) -> TestableRequirementSet | None:
    """Map one run's ``AnalysisResult`` into a ``TestableRequirementSet``.

    *engineering_context* is the complete reasoning input the run's Gemini call
    actually saw — its evidence, across every contributing group, is
    ``traces_to``'s source (see the module docstring). *consolidated_artifact*
    is the run's primary (highest-ranked) group — ``component`` and
    ``functional_tag`` come from it alone, unaffected by the ``traces_to``
    correction.

    Returns ``None`` when *governance_result* is not ``PASS``/``PASS_WITH_WARNINGS``
    (ADR-0034 property 4) — the caller should not write anything in that case.

    Raises:
        TestableRequirementEmissionError: If the response body cannot be parsed,
            or if *engineering_context* carries zero SourceArtifacts across all
            three domains (a requirement that cannot be traced to at least one
            source is never emitted, per this task's own hard-error
            requirement).
    """
    if not gate_permits_emission(governance_result):
        return None

    traces_to = _source_refs(engineering_context)
    if not traces_to:
        raise TestableRequirementEmissionError(
            f"EngineeringContext '{engineering_context.context_id}' carries no SourceArtifacts; "
            "a TestableRequirement cannot be traced to at least one source."
        )

    body = _response_object(analysis_result)
    component = consolidated_artifact.module
    functional_tag = _functional_tag(component)

    requirements: list[TestableRequirement] = []
    for key, category in _REQUIREMENT_ARRAYS:
        for statement in _texts(body, key):
            requirements.append(
                build_testable_requirement(
                    title=statement,
                    component=component,
                    functional_tag=functional_tag,
                    priority=None,
                    traces_to=traces_to,
                    acceptance_criteria=[
                        AcceptanceCriterionInput(category=category, statement=statement)
                    ],
                )
            )

    risks = [
        build_risk(RiskInput(category=None, statement=statement, traces_to=traces_to))
        for statement in _texts(body, _RISK_ARRAY_KEY)
    ]

    prompt_definition = prompt_registry.get(RUNTIME_PROMPT_ID, analysis_result.prompt_version)
    decision = RequirementQualityGovernanceDecision(governance_result.assessment.decision)

    return TestableRequirementSet(
        run_id=run_id,
        generated_at=generated_at or datetime.now(UTC),
        provenance=TestableRequirementSetProvenance(
            prompt_id=prompt_definition.metadata.prompt_id,
            prompt_version=analysis_result.prompt_version,
            prompt_sha256=prompt_definition.metadata.sha256,
            provider=str(analysis_result.provider),
            model=analysis_result.model,
            requirement_quality_governance_decision=decision,
            governance_report_ref="quality_governance_report.md",
        ),
        requirements=requirements,
        risks=risks,
    )


__all__ = [
    "TestableRequirementEmissionError",
    "emit_testable_requirement_set",
    "gate_permits_emission",
]
