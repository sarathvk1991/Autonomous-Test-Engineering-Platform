"""Deterministic stability evaluation (CAP-086B).

``StabilityEvaluator`` is the **sole stability authority**: it is the only
component that evaluates Learning stability across organizational evidence.
Stability answers *has this Learning remained consistently valid across
organizational evidence?* — a concept permanently independent of Confidence
(strength of evidence) and Maturity (organizational adoption), per ADR-0029
D13/Recommendation 17.

**Reserved output (ADR-0029 D13/D10).** `LearningResult`'s frozen shape
carries no dedicated Stability field — this collaborator's decision is
computed deterministically and exercised end to end, but is never threaded
into any persisted model. This mirrors the same reserved-output discipline
ADR-0027 §D14 established for `PromotionRule` ahead of its own engine, and
ADR-0029's own D10 footnote already froze for
:class:`~requirement_intelligence.learning.engine.promotion_recorder.
PromotionRecorder`'s output. A future model-extension milestone may persist
this decision without changing the independence rule this collaborator
already satisfies.

The decision is a deterministic function of already-computed collaborator
output alone — a Learning is stable exactly when it is both validated (true
for every ``Learning`` this engine ever constructs, D9) and already deemed
institutionally ready (D12) — no re-reading of the consumed
``OrganizationalMemoryResult``, no hidden state (D18/D20).
"""

from __future__ import annotations

from requirement_intelligence.learning.identity import LearningId
from requirement_intelligence.learning.models.learning import Learning


class StabilityEvaluator:
    """Decide Learning stability from already-computed institutionalization only."""

    def evaluate(
        self,
        learnings: tuple[Learning, ...],
        institutionalized_ids: frozenset[LearningId],
    ) -> frozenset[LearningId]:
        """Deterministically return the ids of every stable Learning.

        A Learning is stable exactly when it is institutionally ready — the
        one already-computed, already-explainable decision this evaluator
        may consult (D18: no hidden reasoning beyond named collaborator
        output).
        """
        return frozenset(
            learning.learning_id
            for learning in learnings
            if learning.learning_id in institutionalized_ids
        )
