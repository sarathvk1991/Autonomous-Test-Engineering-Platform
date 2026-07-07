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
        The ConsolidatedArtifact that was analysed.
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
    """

    selected: Any
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
