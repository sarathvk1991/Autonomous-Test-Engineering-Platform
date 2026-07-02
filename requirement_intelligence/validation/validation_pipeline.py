"""Validation pipeline — orchestrates ValidationRule execution.

The ValidationPipeline is the single point of execution for the Response
Validation Layer.  It receives a
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`,
asks it for the ordered set of enabled rules, invokes each rule against the
analysed response, collects the findings, and assembles them into the canonical
:class:`~requirement_intelligence.validation.models.validation_result.ValidationResult`.

Design notes
------------
* **Orchestration only.**  The pipeline contains no validation logic, no AI
  knowledge, and no business rules.  It delegates all validation decisions to
  the rules it executes.  This mirrors the separation maintained by the LLM
  provider framework (the factory wires providers; it does not generate text)
  and the connector framework (the registry wires connectors; it does not fetch
  records).

* **Deterministic ordering.**  The pipeline trusts the registry for ordering.
  Rules arrive from
  :meth:`~requirement_intelligence.validation.validation_registry.ValidationRegistry.get_enabled_rules`
  already sorted by architecture-mandated layer order.  The pipeline does not
  re-sort.

* **Future parallel execution.**  The pipeline is designed to support parallel
  evaluation of rules *within* the same layer without any contract change.
  Rule Independence (§3.11) guarantees that parallelisation cannot change the
  finding set.  The current implementation is sequential; the signature and
  return contract are stable for a future concurrent implementation.

* **Derivation, not judgement.**  Assembling the
  :class:`~requirement_intelligence.validation.models.validation_summary.ValidationSummary`,
  the overall verdict, and the run health is pure *derivation* over the issues
  the rules already produced — it rolls findings up, it does not decide
  trustworthiness.  The verdict follows "highest severity wins" exactly as the
  architecture mandates (§6, §8): any ``CRITICAL`` ⇒ ``BLOCKED``; else any
  ``ERROR`` ⇒ ``FAILED``; else any ``WARNING`` ⇒ ``PASSED_WITH_WARNINGS``; else
  ``PASSED``.

* **ValidationResult is the permanent contract.**  :meth:`ValidationPipeline.run`
  *always* returns a fully-populated ``ValidationResult`` — including when no
  rules are registered or zero issues are produced.  An empty result is a valid
  execution, not a placeholder: its summary, statistics, and framework metadata
  are still populated and its verdict is ``PASSED``.  There are no placeholder
  return types anywhere in the framework.

Relationship to other frameworks
---------------------------------
The ValidationPipeline is the structural equivalent of:

* ``RequirementAnalysisService.analyse`` — a coordinating method that calls
  subordinate concerns in order without knowing their internals.
* The consolidation engine — orchestrates a fixed set of steps without owning
  any step's logic.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from enum import Enum

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.validation.models import (
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    ValidationConfiguration,
    ValidationFrameworkMetadata,
    ValidationHealth,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatistics,
    ValidationSummary,
    ValidationVerdict,
)
from requirement_intelligence.validation.models.validation_input import ValidationInput
from requirement_intelligence.validation.validation_exceptions import ValidationPipelineError
from requirement_intelligence.validation.validation_registry import ValidationRegistry
from requirement_intelligence.validation.validation_rule import ValidationRule
from shared.utils.ids import new_id, utc_now


class PipelineState(Enum):
    """Observable lifecycle state of a :class:`ValidationPipeline`.

    The state is **informational only**.  It is exposed for observability and
    debugging; it **never** influences validation behaviour.  No branching
    decision inside the pipeline is taken on the basis of this state, and the
    findings a run produces are identical regardless of how the state is read.

    Members
    -------
    CREATED
        The pipeline object is being constructed but is not yet ready.
    READY
        Construction succeeded; the pipeline is ready to run.  The registry has
        been sealed and the ordered rule set is available.
    RUNNING
        A :meth:`ValidationPipeline.run` call is in progress.
    COMPLETED
        The most recent :meth:`ValidationPipeline.run` call finished
        successfully.
    FAILED
        The most recent :meth:`ValidationPipeline.run` call raised before
        completing.
    DISPOSED
        Reserved for a future explicit teardown step.  Not entered by any
        current transition.

    Transitions
    -----------
    ::

        (construct) ─► CREATED ─► READY ─► RUNNING ─► COMPLETED ─► RUNNING ...
                                              │
                                              └─► FAILED ─► RUNNING ...

        DISPOSED is reserved and is not part of any current transition.
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPOSED = "disposed"  # reserved — no current transition enters this state


class ValidationPipeline:
    """Orchestrates the execution of registered
    :class:`~requirement_intelligence.validation.validation_rule.ValidationRule`
    instances against an AI response.

    The pipeline is the only component that calls ``rule.validate()``.  All
    other components interact with the pipeline through :meth:`run`.

    Usage
    -----
    .. code-block:: python

        registry = ValidationRegistry()
        registry.register(MyTransportRule())
        registry.register(MySyntaxRule())

        pipeline = ValidationPipeline(registry)
        findings = pipeline.run(validation_input)

    Adding a new rule
    -----------------
    Register it with the registry before constructing the pipeline (or use
    :meth:`get_ordered_rules` to inspect the active set).  No pipeline code
    changes.
    """

    def __init__(self, registry: ValidationRegistry) -> None:
        """Construct the pipeline from a populated registry.

        Parameters
        ----------
        registry:
            The :class:`ValidationRegistry` that supplies the ordered rule set.
            The registry must be fully populated before the pipeline is
            constructed.  Construction **seals** the registry: rules cannot be
            registered afterwards, which guarantees the pipeline's rule set is
            fixed for its lifetime.

        Raises
        ------
        ValidationPipelineError
            If *registry* is not a :class:`ValidationRegistry` instance.
        """
        self._state: PipelineState = PipelineState.CREATED
        if not isinstance(registry, ValidationRegistry):
            # Stay in CREATED; construction never reached READY.
            raise ValidationPipelineError(
                f"ValidationPipeline requires a ValidationRegistry instance; "
                f"got {type(registry).__name__!r}."
            )
        self._registry = registry
        # Sealing the registry freezes the rule set for this pipeline's lifetime.
        self._registry.seal()
        self._state = PipelineState.READY

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> PipelineState:
        """The current observable :class:`PipelineState`.

        Informational only — reading this never changes how the pipeline
        behaves, and the pipeline never branches on it.
        """
        return self._state

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def get_ordered_rules(self) -> list[ValidationRule]:
        """Return the ordered set of enabled rules the pipeline will execute.

        Rules are returned in the architecture-mandated layer order (Transport →
        … → Business Rule) with insertion order preserved within each layer.

        Returns
        -------
        list[ValidationRule]
            Enabled rules in deterministic pipeline order.
        """
        return self._registry.get_enabled_rules()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(
        self,
        validation_input: ValidationInput,
        configuration: ValidationConfiguration | None = None,
    ) -> ValidationResult:
        """Validate *validation_input* and return the canonical ``ValidationResult``.

        The pipeline input is the :class:`ValidationInput` (ADR-0003): the binding
        of the analysed response (``analysis_result``) and its normalization output
        (``normalization_result``, carrying the shared ``ParsedResponse`` and the
        observations).  Rules are executed in the order returned by
        :meth:`get_ordered_rules`, each receiving the *same* ``ValidationInput``
        unchanged — Transport rules read ``validation_input.analysis_result``;
        Syntax onward read ``validation_input.normalization_result``.  Their issues
        are collected, a summary and verdict are derived, telemetry is recorded, and
        everything is assembled into a single immutable
        :class:`~requirement_intelligence.validation.models.validation_result.ValidationResult`.

        This is the **permanent framework contract**.  The method *always*
        returns a fully-populated ``ValidationResult``:

        * With **no rules registered** or **zero issues produced**, the result is
          still valid — not a placeholder.  Its summary, statistics, and
          framework metadata are populated, and its verdict is ``PASSED``.
        * The original ``AnalysisResult`` (from ``validation_input``) is preserved
          on the result, unaltered.

        The pipeline never inspects or mutates *validation_input*; it passes it to
        each rule and carries its ``AnalysisResult`` through to the result.

        Future evolution
        ----------------
        * **Fail Fast** — a future revision may inspect each issue's ``blocking``
          indicator and halt progression after a foundational blocking issue.
          That is a behavioural change, deferred to a later task; today every
          enabled rule runs.
        * **Parallel execution** — rules within a layer may be evaluated
          concurrently.  Rule Independence guarantees this is safe.

        Parameters
        ----------
        validation_input:
            The canonical validation input (ADR-0003).  Passed unchanged to each
            rule; its ``AnalysisResult`` is preserved on the returned result.
        configuration:
            The execution policy that governs the run.  When omitted, a
            fully-defaulted :class:`ValidationConfiguration` is used.

        Returns
        -------
        ValidationResult
            The single, immutable output of the framework — always populated.

        Raises
        ------
        ValidationPipelineError
            If *validation_input* is not a :class:`ValidationInput` instance.

        Any exception raised by a rule propagates unchanged after the pipeline
        records the :attr:`PipelineState.FAILED` state — a rule contract failure
        is an infrastructure error, never a validation verdict.
        """
        if not isinstance(validation_input, ValidationInput):
            raise ValidationPipelineError(
                f"ValidationPipeline.run requires a ValidationInput instance; "
                f"got {type(validation_input).__name__!r}."
            )

        analysis_result: AnalysisResult = validation_input.analysis_result
        config = configuration if configuration is not None else ValidationConfiguration()

        self._state = PipelineState.RUNNING
        started_at = utc_now()
        try:
            issues: list[ValidationIssue] = []
            rules_executed = 0
            rules_passed = 0
            rules_failed = 0
            for rule in self.get_ordered_rules():
                rules_executed += 1
                rule_findings = rule.validate(validation_input)
                if rule_findings:
                    rules_failed += 1
                    issues.extend(rule_findings)
                else:
                    rules_passed += 1
        except BaseException:
            # State is observational; record the failure and re-raise the
            # original exception unchanged so existing error handling is
            # unaffected.
            self._state = PipelineState.FAILED
            raise
        completed_at = utc_now()

        result = self._assemble_result(
            analysis_result=analysis_result,
            configuration=config,
            issues=issues,
            rules_executed=rules_executed,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            started_at=started_at,
            completed_at=completed_at,
        )
        self._state = PipelineState.COMPLETED
        return result

    # ------------------------------------------------------------------
    # Result assembly (pure derivation — no validation judgement)
    # ------------------------------------------------------------------

    def _assemble_result(
        self,
        *,
        analysis_result: AnalysisResult,
        configuration: ValidationConfiguration,
        issues: list[ValidationIssue],
        rules_executed: int,
        rules_passed: int,
        rules_failed: int,
        started_at: datetime,
        completed_at: datetime,
    ) -> ValidationResult:
        """Assemble the canonical ``ValidationResult`` from collected issues.

        Pure derivation: rolls up the issues into a summary, derives the verdict
        by "highest severity wins", records telemetry, and stamps framework
        provenance.  No trustworthiness decision is taken here.
        """
        summary = self._derive_summary(issues)
        verdict = self._derive_verdict(issues)
        duration_ms = (completed_at - started_at).total_seconds() * 1000.0

        statistics = ValidationStatistics(
            validation_duration_ms=duration_ms,
            rules_executed=rules_executed,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            started_at=started_at,
            completed_at=completed_at,
            validator_version=FRAMEWORK_VERSION,
            validation_contract_version=configuration.validation_contract_version,
            execution_id=analysis_result.execution_id,
        )

        framework_metadata = ValidationFrameworkMetadata(
            framework_version=FRAMEWORK_VERSION,
            validation_contract_version=configuration.validation_contract_version,
            pipeline_version=PIPELINE_VERSION,
            registry_version=REGISTRY_VERSION,
        )

        return ValidationResult(
            validation_id=new_id(),
            execution_id=analysis_result.execution_id,
            analysis_id=analysis_result.analysis_id,
            analysis_result=analysis_result,
            validation_summary=summary,
            validation_statistics=statistics,
            validation_issues=tuple(issues),
            validation_configuration=configuration,
            validation_framework_metadata=framework_metadata,
            overall_verdict=verdict,
            started_at=started_at,
            completed_at=completed_at,
        )

    @staticmethod
    def _derive_summary(issues: Sequence[ValidationIssue]) -> ValidationSummary:
        """Roll the issue collection up into a derived summary (counts only)."""
        info = sum(1 for i in issues if i.severity == ValidationSeverity.INFO)
        warning = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        error = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        critical = sum(1 for i in issues if i.severity == ValidationSeverity.CRITICAL)
        blocking = sum(1 for i in issues if i.blocking)
        category_counts = dict(Counter(i.category for i in issues))

        return ValidationSummary(
            total_issues=len(issues),
            info_count=info,
            warning_count=warning,
            error_count=error,
            critical_count=critical,
            blocking_issue_count=blocking,
            category_counts=category_counts,
            overall_health=ValidationPipeline._derive_health(
                critical=critical, error=error, warning=warning
            ),
        )

    @staticmethod
    def _derive_verdict(issues: Sequence[ValidationIssue]) -> ValidationVerdict:
        """Derive the overall verdict by "highest severity wins" (§6, §8)."""
        severities = {i.severity for i in issues}
        if ValidationSeverity.CRITICAL in severities:
            return ValidationVerdict.BLOCKED
        if ValidationSeverity.ERROR in severities:
            return ValidationVerdict.FAILED
        if ValidationSeverity.WARNING in severities:
            return ValidationVerdict.PASSED_WITH_WARNINGS
        return ValidationVerdict.PASSED

    @staticmethod
    def _derive_health(*, critical: int, error: int, warning: int) -> ValidationHealth:
        """Map the highest severity present onto the run's qualitative health."""
        if critical > 0:
            return ValidationHealth.CRITICAL
        if error > 0:
            return ValidationHealth.DEGRADED
        if warning > 0:
            return ValidationHealth.WARNING
        return ValidationHealth.HEALTHY
