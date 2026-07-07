"""Platform Context — centralized construction of platform components.

:class:`PlatformContext` is a pure dependency factory. The CLI (and any other
caller) asks it for the components it needs instead of importing and
instantiating each platform class directly. This keeps wiring in one place and
keeps callers thin.

PlatformContext contains **no business logic** — every method only constructs
and returns a platform object.
"""

from __future__ import annotations

from functools import cached_property

from requirement_intelligence.analysis.analysis_configuration import (
    AnalysisConfiguration,
)
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.consolidation.consolidation_engine import (
    ConsolidationEngine,
)
from requirement_intelligence.cp1.response import (
    CP1Service,
    ValidationToCP1Handoff,
    build_cp1_service,
)
from requirement_intelligence.llm.llm_factory import create_provider as _create_provider
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.prompts.requirement_prompt_builder import (
    RequirementPromptBuilder,
)
from requirement_intelligence.registry.connector_registry import ConnectorRegistry
from requirement_intelligence.validation.profiles import (
    ValidationProfileDefinition,
    ValidationProfileRegistry,
)
from requirement_intelligence.validation.response import (
    ResponseValidator,
    build_response_validator,
    build_response_validator_for_profile,
)


class PlatformContext:
    """Factory for platform components. Construction only — no business logic."""

    def create_connector_registry(self) -> ConnectorRegistry:
        """Return a new connector registry (Connectors + Mappers orchestrator)."""
        return ConnectorRegistry()

    def create_consolidation_engine(self) -> ConsolidationEngine:
        """Return a new consolidation engine."""
        return ConsolidationEngine()

    def create_prompt_builder(self) -> RequirementPromptBuilder:
        """Return a new requirement prompt builder."""
        return RequirementPromptBuilder()

    def create_provider(self, provider_name: str, model: str | None = None) -> LLMProvider:
        """Return a provider instance via the platform factory.

        Parameters
        ----------
        provider_name:
            Provider id (e.g. ``"gemini"``).
        model:
            Optional model override; when *None* the provider reads its
            environment-configured model.
        """
        return _create_provider(provider_name, model_name=model)

    def create_analysis_configuration(
        self, reasoning_contract_version: str
    ) -> AnalysisConfiguration:
        """Return an execution configuration carrying the reasoning version."""
        return AnalysisConfiguration(
            reasoning_contract_version=reasoning_contract_version,
        )

    def create_requirement_analysis_service(
        self,
        prompt_builder: RequirementPromptBuilder,
        provider: LLMProvider,
        configuration: AnalysisConfiguration,
    ) -> RequirementAnalysisService:
        """Return the requirement analysis service wired with its collaborators."""
        return RequirementAnalysisService(
            prompt_builder=prompt_builder,
            provider=provider,
            configuration=configuration,
        )

    def create_response_validator(self) -> ResponseValidator:
        """Return a fully wired :class:`ResponseValidator` over every implemented rule.

        Pure composition: delegates to the validation subsystem's composition root
        :func:`~requirement_intelligence.validation.response.build_response_validator`,
        which assembles the registry, pipeline, and validator. This method owns only
        dependency composition — it introduces no validation logic, no caching, and
        no configuration of its own.
        """
        return build_response_validator()

    def get_validation_profile(self, name: str | None = None) -> ValidationProfileDefinition:
        """Return the governed Validation Profile for *name* (default when ``None``).

        Delegates to the :class:`ValidationProfileRegistry`, the sole owner of the
        immutable governed profile definitions. This method owns only selection — it
        never defines profiles, constructs validators, or executes validation.
        """
        return ValidationProfileRegistry().get(name)

    def create_response_validator_for_profile(
        self, profile: ValidationProfileDefinition
    ) -> ResponseValidator:
        """Return a :class:`ResponseValidator` wired for *profile*.

        Pure composition: delegates to the Validation Factory
        (:func:`~requirement_intelligence.validation.response.build_response_validator_for_profile`),
        which builds a registry containing exactly the profile's implemented rules
        and the validator over it. Rule ordering remains governed by ``LAYER_ORDER``;
        the profile only narrows the rule set. This method owns only composition.
        """
        return build_response_validator_for_profile(profile)

    @cached_property
    def cp1_service(self) -> CP1Service:
        """The single :class:`CP1Service` owned by this context (CAP-067B).

        Built **once**, exclusively through the CP1 composition root
        :func:`~requirement_intelligence.cp1.response.build_cp1_service`, and reused for
        every CP1 run. This context constructs **no** registry, pipeline, criterion, or
        engine of its own — the composition root owns that assembly (CAP-066); this
        property owns only the single-instance ownership. ``CP1Service`` holds only
        immutable wiring (a sealed registry + the stateless engine) and builds a fresh
        pipeline per :meth:`~CP1Service.run` call, so a single shared instance is
        deterministic and safe to reuse across runs.
        """
        return build_cp1_service()

    def create_validation_to_cp1_handoff(self) -> ValidationToCP1Handoff:
        """Return the Validation → CP1 handoff seam (CAP-064, ADR-0011 §D4/§D5).

        Pure construction of the stateless seam that gates on the Validation verdict
        and binds a single ``CP1Input``. This method owns only construction — the seam
        owns the gate/bind orchestration; this context invents no gating policy and
        builds no ``CP1Input`` itself.
        """
        return ValidationToCP1Handoff()
