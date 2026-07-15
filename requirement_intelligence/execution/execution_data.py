"""Execution data — the immutable input bundle for the execution package.

:class:`ExecutionData` carries the raw objects produced by one analysis run. The
:class:`~requirement_intelligence.execution.execution_writer.ExecutionWriter` and
the markdown/manifest builders read from it; they never reach back into the CLI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionData:
    """Everything the execution package needs to render one run.

    Fields
    ------
    selected:
        The **primary** contributing ConsolidatedArtifact — the highest-ranked
        group the orchestrator admitted. Persisted verbatim as
        ``consolidated_artifact.json``. Under the active multi-source policy it is
        one of several contributors, and it is *not* the whole of what a reasoner
        saw: ``engineering_context`` is. It remains in the package because a
        context flattens and reorders evidence across its groups and so cannot
        reconstitute a consolidation group, and because the group is the unit
        Consolidation actually produced.
    engineering_context:
        The ``EngineeringContext`` the Engineering Context Orchestrator composed
        and the prompt was built from (CAP-076C). The complete reasoning input,
        and the complete record of how it was chosen. Persisted as
        ``engineering_context.json``. Present for every run, including dry runs:
        the context exists before the provider is ever called.
    prompt_request:
        The built PromptRequest (system/user prompts, version, full prompt).
    llm_request:
        The LLMRequest submitted (or that would be submitted, for a dry run).
    result:
        The AnalysisResult, or ``None`` for a dry run.
    dry_run:
        Whether the provider was skipped.
    provider_name:
        The provider id requested on the command line.
    requested_model:
        The model override requested (may be ``None``).
    reasoning_contract_version:
        The reasoning contract version in force.
    execution_name:
        Optional caller-supplied execution name (else ``None``).
    command_line_arguments:
        Serialisable view of the parsed CLI arguments.
    subcommand:
        The originating subcommand (always ``"analyze"`` today).
    source_artifact_count:
        Number of source artifacts the pipeline produced (engineering metric).
        ``None`` when not supplied.
    consolidated_artifacts:
        The full list of consolidated artifacts the pipeline produced, used for
        engineering metrics (rank, group sizes). Empty when not supplied.
    validation_result:
        The complete ``ValidationResult`` produced by the Response Validator, when
        validation was executed for this run (``--validate`` on a live analysis).
        ``None`` when validation was not executed (default runs, dry runs). The
        execution package owns persistence; it serialises this object as-is.
    validation_profile:
        The governed ``ValidationProfileDefinition`` that selected the executed
        rules, when validation was executed. ``None`` when validation was not
        executed. Recorded alongside the result so the report can display it; the
        profile identity also rides inside the ``ValidationResult`` (its
        configuration metadata), so persistence needs no separate field.
    cp1_result:
        The complete ``CP1Result`` produced by ``CP1Service.run`` when the
        Validation → CP1 handoff opened the gate (validation ``PASSED`` /
        ``PASSED_WITH_WARNINGS``) for a live analysis (CAP-067B). ``None`` when CP1 did
        not execute — no ``--validate``, a dry run, or a closed gate
        (``FAILED`` / ``BLOCKED``). At this milestone the field only **transports** the
        result through the execution flow; no persistence, reporting, or rendering is
        introduced here.
    grounding_result:
        The complete ``GroundingResult`` produced by the Grounding runtime, when grounding
        was executed for this run. ``None`` when grounding did not execute (the default —
        grounding is not yet wired into the CLI run). When present, the execution package
        serialises it as-is into ``grounding_result.json`` / ``grounding_report.md`` /
        ``grounding_metrics.md`` — a pure projection; nothing is recomputed (CAP-077F.1).
    quality_governance_result:
        The complete ``QualityGovernanceResult`` produced by the Quality Governance
        runtime — the terminal governance authority — when Quality Governance ran for this run
        (CAP-080D). Governance runs only when all three consumed peer results are present
        (a live, validated, CP1-gate-open run), so this is ``None`` for any run that did not
        reach that point. When present, the execution package serialises it as-is into
        ``quality_governance_result.json`` / ``quality_governance_report.md`` /
        ``quality_governance_summary.md`` — a pure projection; nothing is re-evaluated,
        re-assessed, re-decided, or recomputed. The recorded ``QualityDecision`` is the
        canonical release verdict; the package consumes it and never overrides it.
    requirement_enhancement_result:
        The complete ``RequirementEnhancementResult`` produced by the Requirement
        Enhancement runtime, strictly downstream of Analysis and upstream of Grounding
        (CAP-081C, ADR-0018 §D9). ``None`` when enhancement did not execute (a dry run,
        or a surfaced-but-non-fatal enhancement failure). When present, the execution
        package serialises it as-is into ``requirement_enhancement_result.json`` /
        ``requirement_enhancement_report.md`` / ``requirement_enhancement_metrics.md`` —
        a pure projection; nothing is re-enriched, re-related, re-observed, or recomputed.
    recommendation_result:
        The complete ``RecommendationResult`` produced by the Recommendation runtime,
        immediately after Quality Governance and at the permanently frozen end of the
        pipeline (CAP-082C, ADR-0019 §D10). ``None`` when recommendation did not
        execute — it runs only when all five consumed peer results are present (a
        live, enhanced, grounded, validated, CP1-gate-open, governed run), so this is
        ``None`` for any run that did not reach that point, or on a
        surfaced-but-non-fatal recommendation failure. When present, the execution
        package serialises it as-is into ``recommendation_result.json`` /
        ``recommendation_report.md`` / ``recommendation_metrics.md`` — a pure
        projection; nothing is re-generated, re-prioritized, re-grouped, re-scored,
        or recomputed.
    """

    selected: Any
    engineering_context: Any
    prompt_request: Any
    llm_request: Any
    result: Any | None
    dry_run: bool
    provider_name: str
    requested_model: str | None
    reasoning_contract_version: str
    execution_name: str | None
    command_line_arguments: dict[str, Any] = field(default_factory=dict)
    subcommand: str = "analyze"
    source_artifact_count: int | None = None
    consolidated_artifacts: list[Any] = field(default_factory=list)
    validation_result: Any | None = None
    validation_profile: Any | None = None
    cp1_result: Any | None = None
    grounding_result: Any | None = None
    quality_governance_result: Any | None = None
    requirement_enhancement_result: Any | None = None
    recommendation_result: Any | None = None

    @property
    def full_prompt(self) -> str:
        """The exact prompt submitted to the provider."""
        return self.prompt_request.full_prompt

    @property
    def generated_text(self) -> str:
        """The raw response text, or ``""`` for a dry run."""
        if self.result is None:
            return ""
        return self.result.llm_response.generated_text or ""
