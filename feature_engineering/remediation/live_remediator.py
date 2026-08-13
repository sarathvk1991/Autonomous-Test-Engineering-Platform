"""The live, provider-backed :class:`FeatureRemediator` implementation.

:class:`LiveFeatureRemediator` is a peer of
:class:`~feature_engineering.remediation.remediator.StubFeatureRemediator`
behind the same seam (`FeatureRemediator`) -- it satisfies the Protocol
unchanged and is the only thing this module adds. It renders the governed
``fix_gherkin_lint`` prompt (v1.0.0) with one dirty `.feature` file's full
current text plus the platform's own lint violations against it, and
returns the model's remediated content. Every downstream mechanic (re-lint,
re-gate via CP2, attempt counting, escalation) still lives in
:mod:`feature_engineering.remediation.loop`, untouched.

Same mechanism as the live content generator, not a parallel one
-------------------------------------------------------------------
Mirrors ``feature_engineering.generation.live_content_generator.LiveFeatureContentGenerator``'s
own structure exactly: an
:class:`~requirement_intelligence.llm.providers.base_provider.LLMProvider` is
constructor-injected, never constructed here -- provider selection
(``llm_factory.create_provider``) and ``validate_connection()`` are the
caller's responsibility. This module never imports ``llm_factory`` (proven by
the same ``test_*_never_imports_llm_factory`` guard every other Layer 2
package carries), and performs no retries -- the platform performs none
anywhere in this call path today. The governed prompt is loaded the same
SHA-verified way (``PromptRegistry`` -> ``PromptLoader`` -> ``manifest.json``),
and the structured input is appended as the prompt's own final ``INPUT:``
section, exactly like the content generator does.

One structural difference from the content generator, and why
-----------------------------------------------------------------
``generate_feature``'s OUTPUT CONTRACT is raw scenario content only -- the
content generator returns the model's response verbatim, no parsing.
``fix_gherkin_lint`` v1.0.0's OUTPUT CONTRACT is a two-part
``---FEATURE---``/``---CHANGES---`` format (the corrected feature text,
then one JSON change-record per line) -- this seam's `remediate()` must
extract the first part before returning, since :class:`FeatureRemediator`'s
contract is "content in, remediated content out," not the two-part response
shape a bare LLM call yields. Extracting a fixed, documented delimiter is
response-handling, not new remediation logic: the loop
(:mod:`.loop`) still re-lints and re-gates whatever this returns, trusting
nothing about it in advance, exactly as it already does for the stub.
"""

from __future__ import annotations

import json
from uuid import uuid4

from feature_engineering.generation.errors import TransportFailureError
from feature_engineering.gherkin_lint.models import Violation
from feature_engineering.prompts.composition import build_prompt_registry
from requirement_intelligence.llm.generation_identity import GenerationIdentity
from requirement_intelligence.llm.llm_models import LLMRequest
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.token_usage import TokenUsageTracker
from shared.enums.base import ExecutionStatus
from shared.prompts.framework.prompt_registry import PromptRegistry

#: This remediator's own token-usage call-type identifier (token-usage-by-
#: stage instrumentation, 2026-08-12 -- Nitin's "Critically"-flagged
#: clarification).
CALL_TYPE = "feature_remediation"

_PROMPT_ID = "fix_gherkin_lint"
_PROMPT_VERSION = "1.0.0"

#: Deterministic sampling by default, matching the platform-wide convention
#: (``LLMRequest.temperature`` itself defaults to 0.0).
_DEFAULT_TEMPERATURE = 0.0

#: `fix_gherkin_lint` v1.0.0's own OUTPUT CONTRACT, verbatim: "a line
#: containing only ---FEATURE--- followed by the corrected feature file's
#: full text. Second, a line containing only ---CHANGES--- followed by one
#: change record per line...". Not reinvented here -- these are the exact,
#: already-registered prompt's own delimiters.
_FEATURE_MARKER = "---FEATURE---"
_CHANGES_MARKER = "---CHANGES---"


class LiveRemediationError(TransportFailureError):
    """Raised when the LLM boundary fails to produce a usable remediation.

    Covers four failure modes at this boundary -- a provider exception
    (including a timeout, which the provider wraps rather than letting an
    SDK exception escape), a non-``COMPLETED`` normalized execution outcome,
    an empty/whitespace-only response, and a response that does not carry
    the prompt's own ``---FEATURE---``/``---CHANGES---`` output contract at
    all (the one failure mode with no analogue in
    :class:`~feature_engineering.generation.live_content_generator.LiveGenerationError`,
    since `generate_feature`'s output has no such structure to violate).
    Anything the model *did* return inside the ``---FEATURE---`` section,
    however malformed as Gherkin, is not this exception's concern -- that is
    the D5 loop's own re-lint/re-gate job, unchanged.

    A subclass of :class:`~feature_engineering.generation.errors.TransportFailureError`
    (2026-08-04, the Layer 1-3 integration run's F1 fix, applied symmetrically
    here): previously subclassed bare ``Exception``, so a transport failure
    during remediation -- the identical shape of bug the run reproduced at
    generation -- was equally uncaught by `feature_engineering.stage.runner`'s
    remediation call site and would have aborted the whole stage. Never
    observed live (live remediation itself is rare), fixed defensively
    alongside the generation-phase case rather than left as a known parallel
    gap.
    """


class LiveFeatureRemediator:
    """``fix_gherkin_lint`` v1.0.0-backed remediator.

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
        ``fix_gherkin_lint`` v1.0.0 from. When *None*, the canonical registry
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
        usage_recorder: TokenUsageTracker | None = None,
    ) -> None:
        self._provider = provider
        registry = prompt_registry if prompt_registry is not None else build_prompt_registry()
        self._definition = registry.get(_PROMPT_ID, _PROMPT_VERSION)
        self._temperature = temperature
        self._usage_recorder = usage_recorder
        self._last_identity: GenerationIdentity | None = None

    @property
    def last_identity(self) -> GenerationIdentity | None:
        """The prompt/model identity of the most recent successful
        :meth:`remediate` call — ``None`` until the first call completes.
        Purely additive (mirrors ``LiveStepDefinitionGenerator.last_identity``'s
        own discipline)."""
        return self._last_identity

    def remediate(self, content: str, violations: tuple[Violation, ...]) -> str:
        """Return a remediated version of `content` addressing `violations`.

        Satisfies :class:`~feature_engineering.remediation.remediator.FeatureRemediator`
        unchanged -- the D5 loop (:mod:`.loop`) re-lints and re-gates
        whatever this returns, exactly as it does for
        :class:`~feature_engineering.remediation.remediator.StubFeatureRemediator`.

        Raises
        ------
        LiveRemediationError
            If the provider call fails (including a timeout), the response's
            normalized ``execution_status`` is not ``COMPLETED``, the
            returned text is empty/whitespace-only, or the response does not
            carry the prompt's own ``---FEATURE---``/``---CHANGES---``
            output contract.
        """
        request = LLMRequest(
            request_id=str(uuid4()),
            prompt=self._build_prompt(content, violations),
            temperature=self._temperature,
            metadata={
                "prompt_id": self._definition.metadata.prompt_id,
                "prompt_version": self._definition.metadata.version,
            },
        )

        try:
            response = self._provider.generate(request)
        except Exception as exc:  # provider boundary catch-all, mirroring
            # LiveFeatureContentGenerator.generate -- no provider-specific
            # exception (including an SDK timeout) is allowed to cross this
            # boundary unwrapped.
            raise LiveRemediationError(f"LLM provider call failed: {exc}") from exc

        if self._usage_recorder is not None:
            self._usage_recorder.record(CALL_TYPE, response.usage)
        self._last_identity = GenerationIdentity(
            prompt_id=self._definition.metadata.prompt_id,
            prompt_version=self._definition.metadata.version,
            prompt_sha256=self._definition.metadata.sha256,
            provider=str(response.provider),
            model=response.model,
        )

        if response.execution_status != ExecutionStatus.COMPLETED:
            raise LiveRemediationError(
                f"LLM execution did not complete (execution_status="
                f"{response.execution_status!r})."
            )

        generated_text = response.generated_text
        if not generated_text or not generated_text.strip():
            raise LiveRemediationError("LLM returned an empty response.")

        return self._extract_feature_content(generated_text)

    def _build_prompt(self, content: str, violations: tuple[Violation, ...]) -> str:
        """Render the governed template plus the structured input.

        Only the two fields `fix_gherkin_lint` v1.0.0's own INPUT CONTRACT
        names -- `feature_content` and `violations` (each `rule`/`line`/
        `message`) -- are serialized. `Violation.file` is deliberately
        omitted: the prompt's INPUT CONTRACT names no such field (the
        platform's own bookkeeping, not something the model needs to fix one
        file's own violations against its own text).
        """
        input_payload = {
            "feature_content": content,
            "violations": [
                {"rule": v.rule, "line": v.line, "message": v.message} for v in violations
            ],
        }
        input_block = json.dumps(input_payload, indent=2, sort_keys=True)
        template = self._definition.content.rstrip("\n")
        return f"{template}\n\nINPUT:\n{input_block}"

    @staticmethod
    def _extract_feature_content(response_text: str) -> str:
        """Pull the ``---FEATURE---``-delimited section out of the model's
        two-part response; never invented, never re-derived from `CHANGES`.

        Strips only the ONE leading newline that terminates the
        ``---FEATURE---`` marker's own line -- never the trailing whitespace
        of the extracted content itself. A well-formed ``.feature`` file
        must end in a newline (`new-line-at-eof`); stripping trailing
        newlines here would silently corrupt an otherwise-correct
        remediation into one that fails re-lint for a reason this parser
        introduced, not one the model or the D5 loop is responsible for.
        """
        if _FEATURE_MARKER not in response_text or _CHANGES_MARKER not in response_text:
            raise LiveRemediationError(
                "response did not contain the expected "
                f"{_FEATURE_MARKER}/{_CHANGES_MARKER} output contract: {response_text!r}"
            )
        after_marker = response_text.split(_FEATURE_MARKER, 1)[1]
        if after_marker.startswith("\n"):
            after_marker = after_marker[1:]
        feature_content, _, _changes_part = after_marker.partition(_CHANGES_MARKER)
        if not feature_content.strip():
            raise LiveRemediationError("extracted feature content was empty.")
        return feature_content


__all__ = ["LiveFeatureRemediator", "LiveRemediationError"]
