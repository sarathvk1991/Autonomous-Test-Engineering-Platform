"""ADR-0050 D5's second build increment: `CachingFeatureContentGenerator`
wrapping :class:`~feature_engineering.generation.live_content_generator.
LiveFeatureContentGenerator` -- the biggest token sink in the measured
distribution (``feature_content_generation``, 45.4% of tokens,
`docs/architecture/mentor-feedback-scoping.md`), the second generator wrapped
after ``step_definition_generation`` (`automation_engineering/generation/
caching_step_definition_generator.py`, ADR-0050's first increment).

:class:`CachingFeatureContentGenerator` satisfies :class:`~feature_engineering.
generation.content_generator.FeatureContentGenerator` unchanged -- a peer of
``LiveFeatureContentGenerator``/``StubFeatureContentGenerator`` behind the
same seam, exactly as ADR-0050 D3 decided. Every downstream consumer
(``assembler.generate_feature_file``, ``feature_engineering/stage/runner.py``)
already reads a generator through this Protocol or via
``getattr(generator, "last_identity", None)`` -- never a concrete class -- so
wrapping a live generator with this decorator requires ZERO changes at any of
those sites (ADR-0050 D3/D4's own blast-radius claim, proven here by
construction, exactly as it was for step-definition generation).

Mirrors ``CachingStepDefinitionGenerator`` exactly -- same store, same key
function, same hit/miss/mismatch mechanics -- because
``LiveFeatureContentGenerator`` has the identical shape
``LiveStepDefinitionGenerator`` does: a deterministic payload dict built
immediately before the LLM call (``build_feature_content_payload``), and an
identity knowable pre-call (``resolve_feature_content_identity``). The one
difference -- ``TransportFailureError`` is a distinct class per package
(``feature_engineering.generation.errors.TransportFailureError``, not
``automation_engineering.errors.TransportFailureError``) -- is why this
module's mismatch error is its own class rather than a shared import.
"""

from __future__ import annotations

from contracts.testable_requirement import TestableRequirement
from feature_engineering.generation.content_generator import FeatureContentGenerator
from feature_engineering.generation.errors import TransportFailureError
from feature_engineering.generation.live_content_generator import (
    build_feature_content_payload,
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

    Mirrors ``automation_engineering.generation.
    caching_step_definition_generator.GenerationCacheIdentityMismatchError``
    exactly (ADR-0050 D1's correctness argument, D4's "a cache that returns a
    wrong artifact is worse than no cache," enforced in code). Subclasses
    this package's own :class:`TransportFailureError` -- not
    ``automation_engineering``'s -- so ``feature_engineering.stage.runner``'s
    existing per-requirement catch site can escalate it exactly like any
    other generation-boundary failure, without a new except-clause.
    """


class CachingFeatureContentGenerator:
    """Wraps a :class:`FeatureContentGenerator` with ADR-0050's
    artifact-level generation cache.

    Parameters
    ----------
    inner:
        The live (or any) :class:`FeatureContentGenerator` this decorator
        wraps. On a MISS, delegated to unchanged. If it exposes its own
        ``last_identity`` property (``LiveFeatureContentGenerator`` does),
        it is compared against ``static_identity`` after every MISS (the
        identity-mismatch safety check, above).
    store:
        The on-disk cache (:class:`~requirement_intelligence.llm.
        generation_cache.GenerationCacheStore`) entries are read from and
        written to. The SAME store instance ``CachingStepDefinitionGenerator``
        uses may be shared here -- the store is generator-agnostic; the key
        already segregates entries by ``prompt_id``.
    static_identity:
        ``inner``'s :class:`GenerationIdentity`, known WITHOUT calling the
        LLM (ADR-0050 D3 Gap 1) -- resolve via
        :func:`~feature_engineering.generation.live_content_generator.
        resolve_feature_content_identity`, supplying the same
        ``provider``/``model`` the caller already chose when constructing
        ``inner``'s own live provider.
    usage_recorder:
        Optional. A HIT records a cache hit against ``call_type``
        (:meth:`~requirement_intelligence.llm.token_usage.TokenUsageTracker.
        record_cache_hit`, ADR-0050 D3 Gap 2's "zero-cost-verified" bucket).
        A MISS records nothing here -- ``inner`` is expected to be
        constructed with the SAME tracker for its own normal token-usage
        recording on a real call; this decorator does not duplicate that.
    call_type:
        The token-usage call-type key a HIT is recorded under. Defaults to
        ``LiveFeatureContentGenerator``'s own ``CALL_TYPE``
        (``"feature_content_generation"``) so a HIT and a MISS for the same
        generator land in the same scorecard bucket.
    """

    def __init__(
        self,
        inner: FeatureContentGenerator,
        store: GenerationCacheStore,
        static_identity: GenerationIdentity,
        *,
        usage_recorder: TokenUsageTracker | None = None,
        call_type: str = "feature_content_generation",
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
        it would read ``LiveFeatureContentGenerator.last_identity`` --
        wrapping is transparent to every consumer of this property."""
        return self._last_identity

    def generate(self, requirement: TestableRequirement) -> str:
        """Return raw scenario/background content for ``requirement`` --
        from the cache on a HIT (no LLM call), from ``inner`` on a MISS (the
        LLM call happens exactly as it would without this wrapper).

        Raises
        ------
        GenerationCacheIdentityMismatchError
            If a MISS's real identity does not match ``static_identity``
            (the pre-call assumption the key was computed from).
        """
        payload = build_feature_content_payload(requirement)
        key = compute_cache_key(self._static_identity, payload)

        cached = self._store.get(key)
        if cached is not None:
            self._last_identity = cached.identity
            if self._usage_recorder is not None:
                self._usage_recorder.record_cache_hit(self._call_type)
            return cached.generated_text

        generated_text = self._inner.generate(requirement)

        actual_identity = getattr(self._inner, "last_identity", None)
        if actual_identity is not None and actual_identity != self._static_identity:
            raise GenerationCacheIdentityMismatchError(
                f"requirement_id={requirement.requirement_id!r}: the wrapped "
                f"generator's real identity ({actual_identity!r}) does not match "
                f"the identity this decorator was constructed with "
                f"({self._static_identity!r}) -- the cache key was computed from "
                "the wrong identity; refusing to store under it rather than risk "
                "a future silent wrong hit."
            )
        identity_to_store = (
            actual_identity if actual_identity is not None else self._static_identity
        )

        self._store.put(
            key,
            GenerationCacheEntry(
                generated_text=generated_text,
                identity=identity_to_store,
                label={"requirement_id": requirement.requirement_id},
            ),
        )
        self._last_identity = identity_to_store
        return generated_text


__all__ = ["CachingFeatureContentGenerator", "GenerationCacheIdentityMismatchError"]
