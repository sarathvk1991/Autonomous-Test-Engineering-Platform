"""Platform Context — centralized construction of platform components.

:class:`PlatformContext` is a pure dependency factory. The CLI (and any other
caller) asks it for the components it needs instead of importing and
instantiating each platform class directly. This keeps wiring in one place and
keeps callers thin.

PlatformContext contains **no business logic** — every method only constructs
and returns a platform object.
"""

from __future__ import annotations

from requirement_intelligence.analysis.analysis_configuration import (
    AnalysisConfiguration,
)
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.consolidation.consolidation_engine import (
    ConsolidationEngine,
)
from requirement_intelligence.llm.llm_factory import create_provider as _create_provider
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.prompts.requirement_prompt_builder import (
    RequirementPromptBuilder,
)
from requirement_intelligence.registry.connector_registry import ConnectorRegistry


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

    def create_provider(
        self, provider_name: str, model: str | None = None
    ) -> LLMProvider:
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
