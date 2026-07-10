"""Requirement Prompt Builder.

Turns an :class:`EngineeringContext` into a provider-agnostic
:class:`PromptRequest`.  The builder **assembles** prompts; it does not author
them.  All fixed prompt wording is resolved from the governed Prompt Registry
(``PromptRegistry`` → ``PromptLoader`` → ``versions/`` → ``manifest.json``).
The builder's own responsibility is limited to rendering the engineering context
into the context block and injecting it into the governed template.

Why a context and not a ``ConsolidatedArtifact`` (CAP-076C)
-----------------------------------------------------------
Before CAP-076C the builder rendered a single consolidation group, which is why
the runtime could only ever show a reasoner one group's evidence (CAP-074B).
It now renders an :class:`EngineeringContext`, the canonical orchestration
model, whose evidence may span several groups. Under the active
``LegacySelectionPolicy`` a context carries exactly one group, so every rendered
byte is unchanged; the join separators below exist for the multi-group contexts
CAP-076D activates and are inert until then.

It knows nothing about Gemini, Azure OpenAI, Anthropic or any specific model,
and it makes no API calls.  ``PromptRequest`` carries the finished prompt and
can be bridged to the frozen, provider-agnostic ``LLMRequest`` contract via
:meth:`PromptRequest.to_llm_request`.

Responsibility boundary
-----------------------
The builder owns **assembly only**.  It does not own prompt content, prompt
governance, the template contract, lifecycle decisions, or version selection:

* Prompt content, metadata and SHA verification — :class:`PromptRegistry`.
* File loading and integrity — :class:`PromptLoader`.
* Template structure — :mod:`...framework.prompt_template_contract`.
* Version selection — an explicit pin supplied by the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.models.source_artifact import SourceArtifact
from requirement_intelligence.prompts import prompt_constants as consts
from requirement_intelligence.prompts.framework.composition import build_prompt_registry
from requirement_intelligence.prompts.framework.prompt_registry import PromptRegistry
from requirement_intelligence.prompts.framework.prompt_template_contract import (
    parse_governed_template,
)
from requirement_intelligence.prompts.models.prompt_definition import PromptDefinition
from shared.contracts.base import Schema

if TYPE_CHECKING:
    from requirement_intelligence.llm.llm_models import LLMRequest

_SECTION_SEPARATOR = "\n\n"

#: Joins the contributing groups' ids on the Consolidation ID header line.
_ID_SEPARATOR = ", "

#: Joins the contributing groups' consolidation reasons on the reason line.
_REASON_SEPARATOR = "; "

#: Identifier of the governed prompt the runtime resolves from the registry.
RUNTIME_PROMPT_ID = "requirement_analysis"


class PromptRequest(Schema):
    """A finished, provider-agnostic prompt ready for an LLM provider.

    Fields
    ------
    system_prompt:
        The role-establishing system prompt.
    user_prompt:
        The analysis + output-format prompt, with the artifact context injected.
    source_consolidated_id:
        Identifiers of the :class:`ConsolidatedArtifact`\\ s whose evidence this
        prompt was built from, retained for traceability. A single id today;
        comma-joined once a context spans several groups.
    prompt_version:
        Semantic version of the prompt contract that produced this request
        (see :data:`~requirement_intelligence.prompts.prompt_constants.PROMPT_VERSION`).
        Carried through for traceability, auditability and regression analysis.
    """

    system_prompt: str
    user_prompt: str
    prompt_version: str
    source_consolidated_id: str | None = None

    @property
    def full_prompt(self) -> str:
        """Return the system and user prompts combined into one string."""
        return f"{self.system_prompt}{_SECTION_SEPARATOR}{self.user_prompt}"

    def to_llm_request(
        self,
        request_id: str,
        temperature: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> LLMRequest:
        """Bridge this prompt to the frozen, provider-agnostic LLMRequest.

        Parameters
        ----------
        request_id:
            Caller-supplied end-to-end trace identifier (mandatory, non-empty).
        temperature:
            Sampling temperature to forward to the provider.
        metadata:
            Optional extra metadata. Caller values are merged in, but the
            framework-controlled keys (``source_consolidated_id`` and
            ``prompt_version``) always win and cannot be overwritten.
        """
        # Imported lazily to keep the prompts package decoupled from the LLM
        # package at import time. ``LLMRequest`` is provider-agnostic.
        from requirement_intelligence.llm.llm_models import LLMRequest

        framework_metadata = {
            "source_consolidated_id": self.source_consolidated_id,
            "prompt_version": self.prompt_version,
        }

        merged: dict[str, Any] = {}
        if metadata:
            merged.update(metadata)
        # Applied last so framework-controlled keys always win.
        merged.update(framework_metadata)

        return LLMRequest(
            request_id=request_id,
            prompt=self.full_prompt,
            temperature=temperature,
            metadata=merged,
        )


class RequirementPromptBuilder:
    """Build a :class:`PromptRequest` from an :class:`EngineeringContext`.

    The builder is deterministic: the same context always yields the same
    prompt.  It holds no provider state.

    Prompt text is resolved once, at construction, from the governed
    :class:`PromptRegistry`; :meth:`build` performs no I/O.

    Parameters
    ----------
    registry:
        The sealed governed registry to resolve the prompt from.  When *None*,
        the canonical registry is composed via
        :func:`~requirement_intelligence.prompts.framework.composition.build_prompt_registry`,
        which loads ``versions/`` and verifies every SHA-256 against
        ``manifest.json``.
    prompt_id / prompt_version:
        The governed ``(prompt_id, version)`` pair the runtime is pinned to.
        Selection is an explicit, reviewable constant rather than a lifecycle
        query, so promoting a new prompt version is a deliberate change.

    Raises
    ------
    PromptFrameworkError
        If the registry cannot be composed, the pinned ``(prompt_id, version)``
        pair is not registered, or the resolved template does not satisfy the
        governed template contract.
    """

    def __init__(
        self,
        registry: PromptRegistry | None = None,
        prompt_id: str = RUNTIME_PROMPT_ID,
        prompt_version: str = consts.PROMPT_VERSION,
    ) -> None:
        self._registry = registry if registry is not None else build_prompt_registry()
        self._definition = self._registry.get(prompt_id, prompt_version)
        self._template = parse_governed_template(self._definition.content)

    @property
    def prompt_definition(self) -> PromptDefinition:
        """The governed :class:`PromptDefinition` this builder is pinned to."""
        return self._definition

    def build(self, context: EngineeringContext) -> PromptRequest:
        """Assemble the complete prompt for the given engineering context.

        Parameters
        ----------
        context:
            The orchestrated engineering context to analyse.

        Returns
        -------
        PromptRequest
            The provider-agnostic prompt request.
        """
        artifact_context = self._render_artifact_context(context)

        return PromptRequest(
            system_prompt=self._template.system_prompt,
            user_prompt=self._template.render_user_prompt(artifact_context),
            prompt_version=self._definition.metadata.version,
            source_consolidated_id=_ID_SEPARATOR.join(
                context.provenance.contributing_consolidated_ids
            ),
        )

    # ------------------------------------------------------------------
    # Internal rendering helpers (data injection only — no prompt wording)
    # ------------------------------------------------------------------

    def _render_artifact_context(self, context: EngineeringContext) -> str:
        """Render the engineering context into the injectable context block.

        The header projects the context onto the same five labelled lines the
        governed template has always carried: the contributing group ids, the
        subject and its business area, the rolled-up risk, and the reason each
        contributing group was grouped. The three domain sections project the
        context's three evidence tuples (CAP-076A Invariant 6).
        """
        contributions = context.provenance.contributions
        reasons = [c.consolidation_reason for c in contributions if c.consolidation_reason]

        header_lines = [
            consts.ARTIFACT_CONTEXT_HEADER,
            f"{consts.LABEL_CONSOLIDATION_ID}: "
            f"{_ID_SEPARATOR.join(context.provenance.contributing_consolidated_ids)}",
            f"{consts.LABEL_MODULE}: {context.subject.label}",
            f"{consts.LABEL_BUSINESS_AREA}: "
            f"{context.subject.business_area or consts.ARTIFACT_FIELD_FALLBACK}",
            f"{consts.LABEL_RISK_LEVEL}: {context.context_metadata.risk_level}",
        ]
        if reasons:
            header_lines.append(
                f"{consts.LABEL_CONSOLIDATION_REASON}: {_REASON_SEPARATOR.join(reasons)}"
            )

        evidence = context.evidence
        sections = [
            self._render_section(consts.FUNCTIONAL_SECTION_HEADER, evidence.functional_artifacts),
            self._render_section(consts.SECURITY_SECTION_HEADER, evidence.security_artifacts),
            self._render_section(consts.QUALITY_SECTION_HEADER, evidence.quality_artifacts),
        ]

        return "\n".join(header_lines) + _SECTION_SEPARATOR + _SECTION_SEPARATOR.join(sections)

    def _render_section(self, header: str, artifacts: Sequence[SourceArtifact]) -> str:
        """Render one domain section, deterministically, preserving list order."""
        lines = [header]
        if not artifacts:
            lines.append(consts.EMPTY_SECTION_PLACEHOLDER)
            return "\n".join(lines)

        for artifact in artifacts:
            lines.append(self._render_artifact_line(artifact))
            if artifact.description:
                lines.append(
                    consts.ARTIFACT_DESCRIPTION_FORMAT.format(description=artifact.description)
                )
        return "\n".join(lines)

    def _render_artifact_line(self, artifact: SourceArtifact) -> str:
        """Render the single-line summary for one source artifact."""
        fallback = consts.ARTIFACT_FIELD_FALLBACK
        return consts.ARTIFACT_LINE_FORMAT.format(
            source_type=artifact.source_type,
            title=artifact.title,
            severity=artifact.severity or fallback,
            priority=artifact.priority or fallback,
            status=artifact.status or fallback,
            component=artifact.component or fallback,
        )
