"""The live, provider-backed :class:`FeatureContentGenerator` implementation.

:class:`LiveFeatureContentGenerator` is a peer of
:class:`~feature_engineering.generation.content_generator.StubFeatureContentGenerator`
behind the same seam -- it satisfies :class:`FeatureContentGenerator` unchanged
and is the only thing this module adds. It renders the governed
``generate_feature`` prompt (v1.1.0) with one :class:`TestableRequirement` and
returns the raw response text; every downstream mechanic (id assignment, tag
scoping, assembly, structural + lint validation) still lives in
:mod:`feature_engineering.generation.assembler`, untouched.

Same mechanism as Layer 1, not a parallel one
-----------------------------------------------
Mirrors ``RequirementAnalysisService``'s own boundary exactly: an
:class:`~requirement_intelligence.llm.providers.base_provider.LLMProvider` is
constructor-injected, never constructed here -- provider selection
(``llm_factory.create_provider``) and ``validate_connection()`` are the
caller's responsibility, exactly as they are the CLI's in
``scripts/run_requirement_analysis.py``, not the analysis service's. This
module never imports ``llm_factory`` (proven by the same
``test_generation_module_never_imports_llm_factory`` guard the core's own
tests already carry), and performs no retries -- the platform performs none
anywhere in this call path today (``RequirementAnalysisService``'s own
docstring: "it does not... retry").

Prompt loading differs from Layer 1 in one respect, by necessity: Layer 1's
``requirement_analysis`` template conforms to the governed system/user
template contract
(:func:`~shared.prompts.framework.prompt_template_contract.parse_governed_template`,
one ``{artifact_context}`` placeholder). ``generate_feature`` v1.1.0 does not
-- it carries no such placeholder, and Layer 2's own composition root
(``feature_engineering/prompts/composition.py``) never parses it through that
contract either. This generator therefore loads the template the same
SHA-verified way (``PromptRegistry`` -> ``PromptLoader`` -> ``manifest.json``)
but appends the structured requirement input as its own final section, rather
than substituting into a placeholder that does not exist in this prompt.
"""

from __future__ import annotations

import json
from uuid import uuid4

from contracts.testable_requirement import TestableRequirement
from feature_engineering.prompts.composition import build_prompt_registry
from requirement_intelligence.llm.llm_models import LLMRequest
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ExecutionStatus
from shared.prompts.framework.prompt_registry import PromptRegistry

_PROMPT_ID = "generate_feature"
_PROMPT_VERSION = "1.1.0"

#: Deterministic sampling by default, matching the platform-wide convention
#: (``LLMRequest.temperature`` itself defaults to 0.0).
_DEFAULT_TEMPERATURE = 0.0


class LiveGenerationError(Exception):
    """Raised when the LLM boundary fails to produce usable content.

    Covers exactly three failure modes at this boundary -- a provider
    exception (including a timeout, which the provider wraps rather than
    letting an SDK exception escape), a non-``COMPLETED`` normalized
    execution outcome, and an empty/whitespace-only response. Anything the
    model *did* return, however malformed as Gherkin, is not this
    exception's concern -- that is the generator core's own, already-proven
    structural and lint validation (``FeatureGenerationError``).
    """


class LiveFeatureContentGenerator:
    """``generate_feature`` v1.1.0-backed content generator.

    Parameters
    ----------
    provider:
        An already-constructed, already-validated
        :class:`LLMProvider` (e.g. via ``llm_factory.create_provider`` +
        ``provider.validate_connection()``, exactly as
        ``scripts/run_requirement_analysis.py`` does for Layer 1). This class
        never selects or constructs a provider itself.
    prompt_registry:
        The sealed Layer 2 :class:`PromptRegistry` to resolve
        ``generate_feature`` v1.1.0 from. When *None*, the canonical registry
        is composed via
        :func:`~feature_engineering.prompts.composition.build_prompt_registry`.
    temperature:
        Sampling temperature forwarded to the provider. Defaults to ``0.0``,
        matching :class:`LLMRequest`'s own platform-wide default.
    """

    def __init__(
        self,
        provider: LLMProvider,
        *,
        prompt_registry: PromptRegistry | None = None,
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> None:
        self._provider = provider
        registry = prompt_registry if prompt_registry is not None else build_prompt_registry()
        self._definition = registry.get(_PROMPT_ID, _PROMPT_VERSION)
        self._temperature = temperature

    def generate(self, requirement: TestableRequirement) -> str:
        """Return raw scenario/background content for *requirement*.

        Raises
        ------
        LiveGenerationError
            If the provider call fails (including a timeout), the response's
            normalized ``execution_status`` is not ``COMPLETED``, or the
            returned text is empty/whitespace-only.
        """
        request = LLMRequest(
            request_id=str(uuid4()),
            prompt=self._build_prompt(requirement),
            temperature=self._temperature,
            metadata={
                "prompt_id": self._definition.metadata.prompt_id,
                "prompt_version": self._definition.metadata.version,
                "requirement_id": requirement.requirement_id,
            },
        )

        try:
            response = self._provider.generate(request)
        except Exception as exc:  # provider boundary catch-all, mirroring
            # RequirementAnalysisService._execute -- no provider-specific
            # exception (including an SDK timeout) is allowed to cross this
            # boundary unwrapped.
            raise LiveGenerationError(
                f"requirement_id={requirement.requirement_id!r}: LLM provider "
                f"call failed: {exc}"
            ) from exc

        if response.execution_status != ExecutionStatus.COMPLETED:
            raise LiveGenerationError(
                f"requirement_id={requirement.requirement_id!r}: LLM execution "
                f"did not complete (execution_status="
                f"{response.execution_status!r})."
            )

        generated_text = response.generated_text
        if not generated_text or not generated_text.strip():
            raise LiveGenerationError(
                f"requirement_id={requirement.requirement_id!r}: LLM returned "
                "an empty response."
            )
        return generated_text

    def _build_prompt(self, requirement: TestableRequirement) -> str:
        """Render the governed template plus the structured requirement input.

        Only the fields ``generate_feature`` v1.1.0's own INPUT CONTRACT
        names -- ``title``, ``narrative``, ``acceptance_criteria`` (each with
        its already-minted ``ac_id``, ``statement``, ``polarity_hints``), and
        ``component`` -- are serialized. ``risks`` is deliberately omitted:
        the governed prompt's INPUT CONTRACT does not name it, and
        ``TestableRequirement.risks`` is always empty in ``contract_version``
        1.0.0 (ADR-0042's own additive correction note; run-level risk data
        lives on ``TestableRequirementSet``, not per-requirement) -- there is
        no honest signal here to serialize.
        """
        input_payload = {
            "title": requirement.title,
            "narrative": requirement.narrative,
            "component": requirement.component,
            "acceptance_criteria": [
                {
                    "ac_id": ac.criterion_id,
                    "statement": ac.statement,
                    "polarity_hints": list(ac.polarity_hints),
                }
                for ac in requirement.acceptance_criteria
            ],
        }
        input_block = json.dumps(input_payload, indent=2, sort_keys=True)
        template = self._definition.content.rstrip("\n")
        return f"{template}\n\nINPUT:\n{input_block}"


__all__ = ["LiveFeatureContentGenerator", "LiveGenerationError"]
