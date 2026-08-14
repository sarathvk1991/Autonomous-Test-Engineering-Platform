"""ADR-0050 D5's third build increment: `CachingTestDataGenerator` wrapping
:class:`~automation_engineering.generation.live_test_data_generator.
LiveTestDataGenerator` -- the other near-equal token sink in the measured
distribution (``test_data_generation``, 43.4%, `docs/architecture/
mentor-feedback-scoping.md`), the third generator wrapped after
``step_definition_generation`` (`automation_engineering/generation/
caching_step_definition_generator.py`, ADR-0050's first increment) and
``feature_content_generation`` (`feature_engineering/generation/
caching_feature_content_generator.py`, ADR-0050's second increment). With
these three, the cache now covers the three biggest sinks in the measured
distribution.

:class:`CachingTestDataGenerator` satisfies :class:`~automation_engineering.
generation.test_data_generator.TestDataGenerator` unchanged -- a peer of
``LiveTestDataGenerator``/``StubTestDataGenerator`` behind the same seam,
exactly as ADR-0050 D3 decided. Every downstream consumer
(``test_data_orchestrator.py``, ``automation_engineering/stage/runner.py``'s
``AssetRecord`` construction) already reads a generator through this Protocol
or via ``getattr(generator, "last_identity", None)`` -- never a concrete
class -- so wrapping a live generator with this decorator requires ZERO
changes at any of those sites (ADR-0050 D3/D4's own blast-radius claim,
proven here by construction, exactly as it was for the first two
generators).

Mirrors ``CachingStepDefinitionGenerator`` more closely than
``CachingFeatureContentGenerator`` does: same package
(``automation_engineering``), same governed-template payload shape, and the
SAME ``TransportFailureError`` hierarchy (``automation_engineering.errors``,
not ``feature_engineering.generation.errors``) -- so this module's mismatch
error reuses the step-def module's own exception class rather than defining
a third, redundant one.
"""

from __future__ import annotations

from automation_engineering.generation.caching_step_definition_generator import (
    GenerationCacheIdentityMismatchError,
)
from automation_engineering.generation.live_test_data_generator import build_test_data_payload
from automation_engineering.generation.test_data_generator import (
    TestDataGenerationContext,
    TestDataGenerator,
)
from requirement_intelligence.llm.generation_cache import (
    GenerationCacheEntry,
    GenerationCacheStore,
    compute_cache_key,
)
from requirement_intelligence.llm.generation_identity import GenerationIdentity
from requirement_intelligence.llm.token_usage import TokenUsageTracker


class CachingTestDataGenerator:
    """Wraps a :class:`TestDataGenerator` with ADR-0050's artifact-level
    generation cache.

    Parameters
    ----------
    inner:
        The live (or any) :class:`TestDataGenerator` this decorator wraps.
        On a MISS, delegated to unchanged. If it exposes its own
        ``last_identity`` property (``LiveTestDataGenerator`` does), it is
        compared against ``static_identity`` after every MISS (the
        identity-mismatch safety check -- see
        :class:`~automation_engineering.generation.
        caching_step_definition_generator.GenerationCacheIdentityMismatchError`,
        reused here unchanged).
    store:
        The on-disk cache (:class:`~requirement_intelligence.llm.
        generation_cache.GenerationCacheStore`) entries are read from and
        written to. The SAME store instance the other two
        ``Caching<X>Generator`` decorators use may be shared here -- the
        store is generator-agnostic; the key already segregates entries by
        ``prompt_id``.
    static_identity:
        ``inner``'s :class:`GenerationIdentity`, known WITHOUT calling the
        LLM (ADR-0050 D3 Gap 1) -- resolve via
        :func:`~automation_engineering.generation.
        live_test_data_generator.resolve_test_data_identity`, supplying the
        same ``provider``/``model`` the caller already chose when
        constructing ``inner``'s own live provider.
    usage_recorder:
        Optional. A HIT records a cache hit against ``call_type``
        (:meth:`~requirement_intelligence.llm.token_usage.TokenUsageTracker.
        record_cache_hit`, ADR-0050 D3 Gap 2's "zero-cost-verified" bucket).
        A MISS records nothing here -- ``inner`` is expected to be
        constructed with the SAME tracker for its own normal token-usage
        recording on a real call; this decorator does not duplicate that.
    call_type:
        The token-usage call-type key a HIT is recorded under. Defaults to
        ``LiveTestDataGenerator``'s own ``CALL_TYPE``
        (``"test_data_generation"``) so a HIT and a MISS for the same
        generator land in the same scorecard bucket.
    """

    def __init__(
        self,
        inner: TestDataGenerator,
        store: GenerationCacheStore,
        static_identity: GenerationIdentity,
        *,
        usage_recorder: TokenUsageTracker | None = None,
        call_type: str = "test_data_generation",
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
        it would read ``LiveTestDataGenerator.last_identity`` -- wrapping is
        transparent to every consumer of this property."""
        return self._last_identity

    def generate(self, context: TestDataGenerationContext) -> str:
        """Return generated Java test-data source for ``context`` -- from
        the cache on a HIT (no LLM call), from ``inner`` on a MISS (the LLM
        call happens exactly as it would without this wrapper).

        Raises
        ------
        GenerationCacheIdentityMismatchError
            If a MISS's real identity does not match ``static_identity``
            (the pre-call assumption the key was computed from).
        """
        payload = build_test_data_payload(context)
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
                f"requirement_id={context.specification.requirement_id!r}: the "
                f"wrapped generator's real identity ({actual_identity!r}) does not "
                f"match the identity this decorator was constructed with "
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
                label={"requirement_id": context.specification.requirement_id},
            ),
        )
        self._last_identity = identity_to_store
        return generated_text


__all__ = ["CachingTestDataGenerator"]
