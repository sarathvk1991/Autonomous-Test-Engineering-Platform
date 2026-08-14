"""ADR-0050 D3/D5's first build increment: the artifact-generation cache's
one Protocol decorator, wrapping :class:`~automation_engineering.generation.
live_step_definition_generator.LiveStepDefinitionGenerator` only -- the
other four generators (page-object, utility, test-data, feature-content) and
the remediator are explicitly out of scope for this increment (ADR-0050 D5).

:class:`CachingStepDefinitionGenerator` satisfies
:class:`~automation_engineering.generation.step_definition_generator.
StepDefinitionGenerator` unchanged -- a peer of ``LiveStepDefinitionGenerator``/
``StubStepDefinitionGenerator`` behind the same seam, exactly as ADR-0050 D3
decided. Every downstream consumer (``orchestrator.py``'s
``orchestrate_step_definition``, ``automation_engineering/stage/runner.py``'s
``AssetRecord`` construction) already reads a generator through this Protocol
or via ``getattr(generator, "last_identity", None)`` -- never a concrete
class -- so wrapping a live generator with this decorator requires ZERO
changes at any of those sites (ADR-0050 D3/D4's own blast-radius claim,
proven here by construction, not merely asserted).
"""

from __future__ import annotations

from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.live_step_definition_generator import (
    build_step_definition_payload,
)
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
    StepDefinitionGenerator,
)
from requirement_intelligence.llm.generation_cache import (
    GenerationCacheEntry,
    GenerationCacheStore,
    compute_cache_key,
)
from requirement_intelligence.llm.generation_identity import GenerationIdentity
from requirement_intelligence.llm.token_usage import TokenUsageTracker


class GenerationCacheIdentityMismatchError(TransportFailureError):
    """Raised when a MISS's real, post-call identity does not match the
    ``static_identity`` the caller supplied at construction time.

    This is the safety check ADR-0050's own D1 correctness argument demands:
    the cache key is computed, pre-call, from ``static_identity`` (ADR-0050
    D3's "Gap 1" closure) -- if the wrapped generator's real identity ever
    diverges from what the caller claimed (a stale ``model=`` string, a
    misconfigured ``provider=``), storing the result under the
    pre-call-assumed key would silently corrupt every future lookup of that
    key. Raising here, loudly, once, is strictly safer than a cache that
    might return a wrong artifact -- ADR-0050 D4's own "a cache that returns
    a wrong artifact is worse than no cache," enforced in code, not just
    stated in the ADR. Subclasses :class:`TransportFailureError` so an
    existing per-need catch site (``automation_engineering/stage/runner.py``)
    can escalate it exactly like any other generation-boundary failure,
    without a new except-clause.
    """


class CachingStepDefinitionGenerator:
    """Wraps a :class:`StepDefinitionGenerator` with ADR-0050's
    artifact-level generation cache.

    Parameters
    ----------
    inner:
        The live (or any) :class:`StepDefinitionGenerator` this decorator
        wraps. On a MISS, delegated to unchanged. If it exposes its own
        ``last_identity`` property (``LiveStepDefinitionGenerator`` does),
        it is compared against ``static_identity`` after every MISS (the
        identity-mismatch safety check, above).
    store:
        The on-disk cache (:class:`~requirement_intelligence.llm.
        generation_cache.GenerationCacheStore`) entries are read from and
        written to.
    static_identity:
        ``inner``'s :class:`GenerationIdentity`, known WITHOUT calling the
        LLM (ADR-0050 D3 Gap 1) -- resolve via
        :func:`~automation_engineering.generation.
        live_step_definition_generator.resolve_step_definition_identity`,
        supplying the same ``provider``/``model`` the caller already chose
        when constructing ``inner``'s own live provider.
    usage_recorder:
        Optional. A HIT records a cache hit against ``call_type``
        (:meth:`~requirement_intelligence.llm.token_usage.TokenUsageTracker.
        record_cache_hit`, ADR-0050 D3 Gap 2's "zero-cost-verified" bucket).
        A MISS records nothing here -- ``inner`` is expected to be
        constructed with the SAME tracker for its own normal token-usage
        recording on a real call; this decorator does not duplicate that.
    call_type:
        The token-usage call-type key a HIT is recorded under. Defaults to
        ``LiveStepDefinitionGenerator``'s own ``CALL_TYPE``
        (``"step_definition_generation"``) so a HIT and a MISS for the same
        generator land in the same scorecard bucket.
    """

    def __init__(
        self,
        inner: StepDefinitionGenerator,
        store: GenerationCacheStore,
        static_identity: GenerationIdentity,
        *,
        usage_recorder: TokenUsageTracker | None = None,
        call_type: str = "step_definition_generation",
    ) -> None:
        self._inner = inner
        self._store = store
        self._static_identity = static_identity
        self._usage_recorder = usage_recorder
        self._call_type = call_type
        self._last_identity: GenerationIdentity | None = None

    @property
    def last_identity(self) -> GenerationIdentity | None:
        """The identity of the most recent :meth:`generate` call -- the
        STORED identity on a HIT, ``inner``'s own real identity on a MISS.
        ``None`` until the first call completes. Read by every downstream
        site via ``getattr(generator, "last_identity", None)``, exactly as
        it would read ``LiveStepDefinitionGenerator.last_identity`` --
        wrapping is transparent to every consumer of this property."""
        return self._last_identity

    def generate(self, context: StepDefinitionGenerationContext) -> str:
        """Return generated Java step-definition source for ``context`` --
        from the cache on a HIT (no LLM call), from ``inner`` on a MISS
        (the LLM call happens exactly as it would without this wrapper).

        Raises
        ------
        GenerationCacheIdentityMismatchError
            If a MISS's real identity does not match ``static_identity``
            (the pre-call assumption the key was computed from).
        """
        payload = build_step_definition_payload(context)
        key = compute_cache_key(self._static_identity, payload)

        cached = self._store.get(key)
        if cached is not None:
            self._last_identity = cached.identity
            if self._usage_recorder is not None:
                self._usage_recorder.record_cache_hit(self._call_type)
            return cached.generated_text

        generated_text = self._inner.generate(context)

        actual_identity = getattr(self._inner, "last_identity", None)
        if actual_identity is not None and actual_identity != self._static_identity:
            raise GenerationCacheIdentityMismatchError(
                f"step_text={context.need.text!r}: the wrapped generator's real "
                f"identity ({actual_identity!r}) does not match the identity this "
                f"decorator was constructed with ({self._static_identity!r}) -- the "
                "cache key was computed from the wrong identity; refusing to store "
                "under it rather than risk a future silent wrong hit."
            )
        identity_to_store = (
            actual_identity if actual_identity is not None else self._static_identity
        )

        self._store.put(
            key,
            GenerationCacheEntry(
                generated_text=generated_text,
                identity=identity_to_store,
                label={"step_text": context.need.text},
            ),
        )
        self._last_identity = identity_to_store
        return generated_text


__all__ = ["CachingStepDefinitionGenerator", "GenerationCacheIdentityMismatchError"]
