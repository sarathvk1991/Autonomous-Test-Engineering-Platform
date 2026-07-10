"""Requirement Analysis Service — the single orchestration boundary for AI execution.

This service coordinates one AI analysis end-to-end:

    EngineeringContext
        → Prompt Builder → PromptRequest → LLMRequest
        → LLM Provider → LLMResponse
        → AnalysisResult

Its input is the canonical orchestration model produced by the Engineering
Context Orchestrator, never a raw consolidation group (CAP-076C). The service
selects nothing: by the time a context reaches it, every evidence decision has
already been made, and explained, by the orchestrator.

It performs **orchestration only**.  Per
``docs/architecture/requirement-analysis-service.md`` it does not validate,
interpret, judge, persist, report, log, retry, cache, or ingest.  It does not
import connectors, mappers, the consolidation engine, validators, CP1, or the
output writer, and it never depends on a concrete provider implementation.

Collaborators (prompt builder and provider) are injected; the service never
instantiates them itself.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from requirement_intelligence.analysis.analysis_configuration import (
    AnalysisConfiguration,
)
from requirement_intelligence.analysis.analysis_exceptions import (
    AnalysisConfigurationError,
    AnalysisError,
    AnalysisExecutionError,
    PromptGenerationError,
    ProviderExecutionError,
)
from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.prompts.requirement_prompt_builder import (
    PromptRequest,
    RequirementPromptBuilder,
)

#: Joins the contributing group ids recorded on an ``AnalysisResult``. Matches
#: the separator the prompt builder uses, so the two can never disagree.
_ID_SEPARATOR = ", "


class RequirementAnalysisService:
    """Coordinate a single AI analysis of one engineering context.

    The service is the exclusive orchestration entry point for AI execution; no
    other component invokes a provider directly.  Its only public method is
    :meth:`analyze`.
    """

    def __init__(
        self,
        prompt_builder: RequirementPromptBuilder,
        provider: LLMProvider,
        configuration: AnalysisConfiguration,
    ) -> None:
        """Inject the orchestration collaborators and execution configuration.

        Parameters
        ----------
        prompt_builder:
            Builds a versioned :class:`PromptRequest` from an engineering context.
        provider:
            The provider-agnostic LLM provider abstraction used for execution.
        configuration:
            The immutable :class:`AnalysisConfiguration` defining execution
            policy (reasoning contract version and future run-time policies).

        Raises
        ------
        AnalysisConfigurationError
            If a required collaborator or the configuration is missing.  Detected
            before any AI call is attempted.
        """
        if prompt_builder is None:
            raise AnalysisConfigurationError("A prompt builder must be provided.")
        if provider is None:
            raise AnalysisConfigurationError("An LLM provider must be provided.")
        if configuration is None:
            raise AnalysisConfigurationError("An analysis configuration must be provided.")

        self._prompt_builder = prompt_builder
        self._provider = provider
        self._configuration = configuration

    # ------------------------------------------------------------------
    # Public API (frozen for Phase 1)
    # ------------------------------------------------------------------

    def analyze(self, context: EngineeringContext) -> AnalysisResult:
        """Orchestrate one AI analysis and return its result.

        The returned :class:`AnalysisResult` is **raw and un-validated**; whether
        the AI answer is acceptable is decided downstream, not here.

        Raises
        ------
        PromptGenerationError
            If the prompt cannot be built or converted into a request.
        ProviderExecutionError
            If the provider fails to execute the request (any provider-specific
            failure is wrapped — none leak out).
        AnalysisExecutionError
            For any unexpected orchestration failure.
        """
        try:
            return self._orchestrate(context)
        except AnalysisError:
            # Already a typed orchestration error — surface as-is.
            raise
        except Exception as exc:  # orchestration boundary catch-all
            raise AnalysisExecutionError(
                f"Unexpected failure during analysis orchestration: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal orchestration steps
    # ------------------------------------------------------------------

    def _orchestrate(self, context: EngineeringContext) -> AnalysisResult:
        # Step 1 — generate the prompt request.
        prompt_request = self._build_prompt(context)

        # Step 2 — generate request identifiers.
        analysis_id = str(uuid4())
        execution_id = str(uuid4())

        # Step 3 — convert PromptRequest → LLMRequest (request_id = execution_id).
        llm_request = self._to_llm_request(prompt_request, execution_id)

        # Step 4 — capture start timestamp.
        started_at = datetime.now(UTC)

        # Step 5 — invoke the provider.
        llm_response = self._execute(llm_request)

        # Step 6 — capture completion timestamp and compute duration.
        completed_at = datetime.now(UTC)
        duration_ms = round((completed_at - started_at).total_seconds() * 1000.0, 2)

        # Step 7 — construct and return the AnalysisResult.
        return AnalysisResult(
            analysis_id=analysis_id,
            execution_id=execution_id,
            source_consolidated_id=_ID_SEPARATOR.join(
                context.provenance.contributing_consolidated_ids
            ),
            prompt_version=prompt_request.prompt_version,
            reasoning_contract_version=self._configuration.reasoning_contract_version,
            provider=llm_response.provider,
            model=llm_response.model,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            llm_response=llm_response,
            metadata=dict(llm_request.metadata),
        )

    def _build_prompt(self, context: EngineeringContext) -> PromptRequest:
        """Delegate prompt construction to the prompt builder (Step 1)."""
        try:
            return self._prompt_builder.build(context)
        except Exception as exc:  # classify as prompt-generation failure
            raise PromptGenerationError(f"Prompt generation failed: {exc}") from exc

    def _to_llm_request(self, prompt_request: PromptRequest, execution_id: str) -> LLMRequest:
        """Convert the prompt request into a provider-agnostic request (Step 3)."""
        try:
            return prompt_request.to_llm_request(request_id=execution_id)
        except Exception as exc:  # classify as prompt-generation failure
            raise PromptGenerationError(f"Prompt request conversion failed: {exc}") from exc

    def _execute(self, llm_request: LLMRequest) -> LLMResponse:
        """Dispatch the request through the provider abstraction (Step 5).

        Any provider-specific exception is wrapped so it does not cross the
        orchestration boundary.
        """
        try:
            return self._provider.generate(llm_request)
        except Exception as exc:  # wrap provider-specific failures
            raise ProviderExecutionError(f"Provider execution failed: {exc}") from exc
