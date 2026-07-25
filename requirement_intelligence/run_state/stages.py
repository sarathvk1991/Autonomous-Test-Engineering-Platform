"""The canonical stage definitions (ADR-0036), with one reported divergence.

ADR-0036's table numbers 19 stages 1-19 and states "Stages 1-13 exist and run
today, synchronously, in this exact order, inside the current CLI." Re-verified
directly against ``scripts/run_requirement_analysis.py`` for this
implementation: that claim does not hold. Two concrete findings:

1. Stage 9 ("Execution Package (write)") is numbered before stages 10-13
   (Continuous Improvement, Knowledge Graph, Organizational Memory, Learning),
   but the CLI's actual execution order runs it LAST — after all four of them
   — because ``ExecutionData`` is assembled and ``ExecutionWriter().write()``
   is called exactly once, at the very end, after every phase has completed in
   memory. Using ADR-0036's literal "#" order for resume decisions would be
   incorrect: a crash after Continuous Improvement/Knowledge Graph succeed but
   before Organizational Memory/Learning run would make "first non-SUCCEEDED
   in # order" point at stage 9, which depends on 10-13's results and is not
   actually safe to run yet.
2. TestableRequirementSet Emission (ADR-0034/ADR-0042, decided the same day as
   ADR-0036) is a real, distinct, gated phase in the live CLI — it runs
   between Requirement Quality Governance and Recommendation — but is not in
   ADR-0036's original 19-stage table at all.

Resolution (reported, not silently applied): ``STAGE_DEFINITIONS`` below is
ordered by actual execution/dependency sequence, the only order for which
"resume from the first non-SUCCEEDED stage" is correct. Each live stage still
carries its ADR-0036 ``#`` as ``stage_number`` for citation.
Testable requirement emission carries ``stage_number=None`` and is flagged in
its own citation field.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageDefinition:
    """Static identity for one stage — never run-specific data."""

    stage_id: str
    stage_number: int | None
    layer: str
    name: str
    governing_citation: str


#: Ordered by actual execution/dependency sequence (see module docstring).
#: The 13 ADR-0036-numbered live stages, plus testable_requirement_emission
#: (ADR-0034/ADR-0042, not in ADR-0036's table), plus the 6 ADR-0036 Layer
#: 2-7 reserved placeholders (declared, not implemented).
STAGE_DEFINITIONS: tuple[StageDefinition, ...] = (
    StageDefinition(
        "engineering_context_orch",
        1,
        "L1",
        "Engineering Context Orchestration",
        "ADR-0015",
    ),
    StageDefinition("requirement_analysis", 2, "L1", "Requirement Analysis", "CAP-014"),
    StageDefinition("requirement_enhancement", 3, "L1", "Requirement Enhancement", "ADR-0018"),
    StageDefinition("grounding", 4, "L1", "Grounding", "ADR-0016"),
    StageDefinition("validation", 5, "L1", "Validation", "pre-ADR architecture docs"),
    StageDefinition("cp1", 6, "L1", "CP1", "ADR-0011/0012/0013"),
    StageDefinition(
        "requirement_quality_governance", 7, "L1", "Requirement Quality Governance", "ADR-0017"
    ),
    StageDefinition(
        "testable_requirement_emission",
        None,
        "L1",
        "TestableRequirementSet Emission",
        "ADR-0034/ADR-0042 (not in ADR-0036's table)",
    ),
    StageDefinition("recommendation", 8, "L1", "Recommendation", "ADR-0019"),
    StageDefinition("continuous_improvement", 10, "L1", "Continuous Improvement", "ADR-0022"),
    StageDefinition("knowledge_graph", 11, "L1", "Knowledge Graph", "ADR-0023"),
    StageDefinition("organizational_memory", 12, "L1", "Organizational Memory", "ADR-0027"),
    StageDefinition("learning", 13, "L1", "Learning", "ADR-0028/0029"),
    StageDefinition(
        "execution_package_write", 9, "L1", "Execution Package (write)", "CAP-020/022"
    ),
    StageDefinition("feature_engineering", 14, "L2", "Feature Engineering", "none yet"),
    StageDefinition("automation_engineering", 15, "L3", "Automation Engineering", "none yet"),
    StageDefinition("suite_quality_governance", 16, "L4", "Suite Quality Governance", "none yet"),
    StageDefinition("test_execution", 17, "L5", "Test Execution", "none yet"),
    StageDefinition(
        "failure_intelligence_self_healing",
        18,
        "L6",
        "Failure Intelligence & Self-Healing",
        "none yet",
    ),
    StageDefinition(
        "governance_dashboard",
        19,
        "L7",
        "Governance Dashboard",
        "none yet, structurally different (ADR-0036 D5)",
    ),
)

#: Stage ids that exist and run today (stages 1-13 of ADR-0036 plus
#: testable_requirement_emission). Layers 2-7 are reserved PENDING placeholders.
LIVE_STAGE_IDS: tuple[str, ...] = tuple(
    d.stage_id
    for d in STAGE_DEFINITIONS
    if d.layer == "L1"
)

PLACEHOLDER_STAGE_IDS: tuple[str, ...] = tuple(
    d.stage_id for d in STAGE_DEFINITIONS if d.layer != "L1"
)

_BY_ID = {d.stage_id: d for d in STAGE_DEFINITIONS}


def stage_definition(stage_id: str) -> StageDefinition:
    """Look up one stage's static definition by id."""
    try:
        return _BY_ID[stage_id]
    except KeyError:
        raise ValueError(f"Unknown stage_id {stage_id!r}") from None


__all__ = [
    "LIVE_STAGE_IDS",
    "PLACEHOLDER_STAGE_IDS",
    "STAGE_DEFINITIONS",
    "StageDefinition",
    "stage_definition",
]
