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

**One batched call per `match()`.** Every step-definition asset in the
catalog plus the need's own text are embedded together, in one
`EmbeddingProvider.embed(...)` call -- ADR-0044 D3's own batching rationale,
realized. There is no per-run caching of computed vectors in this class
(a future optimization, not required for correctness): the catalog itself
already only changes at run-start reconciliation (ADR-0044 D3), so
re-embedding the same unchanged catalog every `match()` call within a run is
a performance concern, not a correctness one.

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

import math

from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.reuse.embeddings import EmbeddingProvider
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embedding_text(asset: StepDefinitionAsset) -> str:
    """The text embedded for one step-definition asset -- its own pattern
    (the literal Gherkin-annotation text) plus its recorded semantic tags
    (`automation_engineering.catalog.java_source.semantic_tags_from_pattern`/
    `semantic_tags_from_identifier`, LLD §7's `supportedActions` analogue).
    Both are already-recorded catalog data; nothing is re-derived here."""
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

    def match(self, need: GherkinStepNeed, catalog: AssetCatalog) -> tuple[MatchCandidate, ...]:
        assets = catalog.step_definitions
        if not assets:
            return ()

        texts = [need.text, *(_embedding_text(asset) for asset in assets)]
        vectors = self._embedding_provider.embed(texts)
        need_vector, *asset_vectors = vectors

        scored = [
            MatchCandidate(
                asset_id=asset.asset_id,
                confidence=_cosine_similarity(need_vector, asset_vector),
                content_hash=asset.content_hash,
            )
            for asset, asset_vector in zip(assets, asset_vectors, strict=True)
        ]
        scored.sort(key=lambda candidate: candidate.confidence, reverse=True)
        return tuple(scored)


__all__ = ["LiveSemanticMatcher"]
