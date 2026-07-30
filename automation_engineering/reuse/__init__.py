"""Layer 3's reuse decision (ADR-0044 D4) -- the REUSE DECISION only.

Builds, against the now-complete asset catalog
(:mod:`automation_engineering.catalog`):

* :mod:`.models` -- the decision domain (`GherkinStepNeed`, `MatchCandidate`,
  `TrustedReuse`/`Escalation`/`NoMatch`).
* :mod:`.matcher` -- the `SemanticMatcher` seam and its deterministic stub.
* :mod:`.embeddings` / :mod:`.live_matcher` -- the live, embeddings-backed
  matcher (ADR-0044 D3's TBD, resolved).
* :mod:`.engine` -- `decide_reuse`, the three-check trust decision
  (ADR-0044 D4).

Deliberately NOT built here: the generators that act on `NoMatch`/
`TrustedReuse` (a future task); CP3/CP4; promotion (ADR-0045).
"""

from __future__ import annotations

from automation_engineering.reuse.embeddings import (
    EmbeddingCallError,
    EmbeddingConfigurationError,
    EmbeddingProvider,
    GeminiEmbeddingProvider,
)
from automation_engineering.reuse.engine import DEFAULT_CONFIDENCE_THRESHOLD, decide_reuse
from automation_engineering.reuse.live_matcher import LiveSemanticMatcher
from automation_engineering.reuse.matcher import SemanticMatcher, StubSemanticMatcher
from automation_engineering.reuse.models import (
    Escalation,
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
    NoMatch,
    ReuseDecision,
    TrustedReuse,
)

__all__ = [
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "EmbeddingCallError",
    "EmbeddingConfigurationError",
    "EmbeddingProvider",
    "Escalation",
    "EscalationCheck",
    "GeminiEmbeddingProvider",
    "GherkinStepNeed",
    "LiveSemanticMatcher",
    "MatchCandidate",
    "NoMatch",
    "ReuseDecision",
    "SemanticMatcher",
    "StubSemanticMatcher",
    "TrustedReuse",
    "decide_reuse",
]
