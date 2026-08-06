"""The live :class:`~automation_engineering.reuse.matcher.SemanticMatcher`
implementation -- embeddings, per ADR-0044 D3's own lean ("Embeddings are
cheaper, batchable across a run's full step set, and cacheable across runs"),
resolving D3's TBD rather than a per-step LLM call.

:class:`LiveSemanticMatcher` is a peer of
:class:`~automation_engineering.reuse.matcher.StubSemanticMatcher` behind the
same :class:`~automation_engineering.reuse.matcher.SemanticMatcher` seam -- it
satisfies the Protocol unchanged and is the only thing this module adds. The
reuse engine (:mod:`.engine`) never imports this module, mirroring
`LiveFeatureContentGenerator`'s/`LiveFeatureRemediator`'s own constructor-
injection discipline exactly: an
:class:`~automation_engineering.reuse.embeddings.EmbeddingProvider` is
constructor-injected here, never constructed by the engine.

**One batched call per `match()` -- and, since the free-tier survivability
build (2026-08-05), at most one batched call for the WHOLE RUN.** Every
step-definition asset in the catalog plus the need's own text are embedded
together, in one `EmbeddingProvider.embed(...)` call -- ADR-0044 D3's own
batching rationale, realized within one `match()` call. That alone was not
the full rationale: a run with N needs still made N calls, one per `match()`,
each RE-embedding the same unchanged catalog every time (the module's own
prior text called this "a performance concern, not a correctness one" --
true in isolation, but a live free-tier run measured N calls against a
100/minute quota as the actual failure mode, not a mere inefficiency).

`prime(needs, catalog)` closes that gap: called once, before any `match()`
call, it embeds every need's text plus every catalog asset's text together,
in as few `EmbeddingProvider.embed(...)` calls as the provider needs (batched
internally there), and caches the result by exact text. Every subsequent
`match()` call within the same run then finds its own texts already cached
and makes ZERO further `embed(...)` calls. `prime()` is optional -- a caller
that never calls it (every existing test that constructs `match()` calls
directly) gets EXACTLY the pre-existing behavior: `match()` embeds on a cache
miss, one call per invocation, correctness unchanged either way. The cache is
keyed by exact text, not by need/asset identity, so priming with a superset
of what `match()` later asks for (or asking for a mix of primed and
never-primed texts) is always safe -- a hit is a hit regardless of how the
vector got there.

**Cosine similarity is the confidence score.** Embedding vectors from this
model family are typically near-unit-norm with non-negative pairwise
similarity for related text, so plain cosine similarity already lands close
to `automation_engineering.reuse.engine`'s own `[0.0, 1.0]`-by-convention
scale without extra rescaling; this is recorded as an implementation choice,
not a guarantee the SDK makes contractually -- real calibration against a
live model is deferred to whenever a `GOOGLE_API_KEY` is actually available
to test against (this environment has none, verified directly).

**Only step definitions are matched.** A :class:`GherkinStepNeed` is a
Gherkin step; page objects and utilities have no comparable "does this step
match" question (:mod:`.engine`'s own signature-fit check already scopes
itself the same way) -- this matcher only ever considers
`catalog.step_definitions`.
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.reuse.embeddings import EmbeddingProvider, cosine_similarity
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate


def step_definition_embedding_text(asset: StepDefinitionAsset) -> str:
    """The text embedded for one step-definition asset -- its own pattern
    (the literal Gherkin-annotation text) plus its recorded semantic tags
    (`automation_engineering.catalog.java_source.semantic_tags_from_pattern`/
    `semantic_tags_from_identifier`, LLD §7's `supportedActions` analogue).
    Both are already-recorded catalog data; nothing is re-derived here.

    **Public** (promoted from a private helper, ADR-0046 D7's "promote,
    don't duplicate" discipline): CP5's orphaned-glue semantic hint
    (:mod:`automation_engineering.cp5.orphaned_glue`) embeds an orphaned
    asset's own text using this SAME recipe, so a catalogued asset is
    represented identically whether the reuse engine or CP5 is the one
    embedding it."""
    return " ".join((asset.pattern, *asset.semantic_tags))


class LiveSemanticMatcher:
    """Embeddings-backed :class:`~automation_engineering.reuse.matcher.SemanticMatcher`.

    Parameters
    ----------
    embedding_provider:
        An already-constructed :class:`EmbeddingProvider` (e.g.
        :class:`~automation_engineering.reuse.embeddings.GeminiEmbeddingProvider`).
        This class never selects or constructs a provider itself, mirroring
        `LiveFeatureContentGenerator`'s own constructor-injection discipline.
    """

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._embedding_provider = embedding_provider
        self._vector_cache: dict[str, tuple[float, ...]] = {}

    def prime(self, needs: Sequence[GherkinStepNeed], catalog: AssetCatalog) -> None:
        """Warm the whole run's vector cache in as few `embed(...)` calls as
        the provider needs, instead of one call per later `match()`. Safe to
        call with an empty `needs`/`catalog.step_definitions` (embeds
        nothing); safe to call more than once (only ever embeds texts not
        already cached)."""
        texts = [need.text for need in needs]
        texts.extend(step_definition_embedding_text(asset) for asset in catalog.step_definitions)
        self._embed_and_cache(texts)

    def match(self, need: GherkinStepNeed, catalog: AssetCatalog) -> tuple[MatchCandidate, ...]:
        assets = catalog.step_definitions
        if not assets:
            return ()

        texts = [need.text, *(step_definition_embedding_text(asset) for asset in assets)]
        self._embed_and_cache(texts)
        need_vector, *asset_vectors = (self._vector_cache[text] for text in texts)

        scored = [
            MatchCandidate(
                asset_id=asset.asset_id,
                confidence=cosine_similarity(need_vector, asset_vector),
                content_hash=asset.content_hash,
            )
            for asset, asset_vector in zip(assets, asset_vectors, strict=True)
        ]
        scored.sort(key=lambda candidate: candidate.confidence, reverse=True)
        return tuple(scored)

    def _embed_and_cache(self, texts: list[str]) -> None:
        """Embed every text in `texts` not already in the cache, in ONE
        `EmbeddingProvider.embed(...)` call (deduplicated -- a text repeated
        within `texts`, e.g. the same catalog asset reappearing across
        several needs, is only ever sent once), and cache the result. A
        no-op when every text is already cached (the steady-state case once
        `prime()` has run)."""
        missing = list(dict.fromkeys(text for text in texts if text not in self._vector_cache))
        if not missing:
            return
        vectors = self._embedding_provider.embed(missing)
        self._vector_cache.update(zip(missing, vectors, strict=True))


__all__ = ["LiveSemanticMatcher", "step_definition_embedding_text"]
