"""ADR-0051 D2's regression gate: compare a candidate
:class:`~eval_harness.models.EvalScore` against a generator's own STORED
baseline -- never an absolute score threshold (the "pass-bias
meaning-check" trap a hardcoded numeric bar risks, already flagged
elsewhere in this arc).

The store shape mirrors ADR-0050 D2's own precedent: reuses
:mod:`~requirement_intelligence.run_state.atomic_write` verbatim (the same
durable-write primitive the artifact-generation cache already uses) rather
than reimplementing atomic writes a second time. It does **not** reuse
:class:`~requirement_intelligence.llm.generation_cache.GenerationCacheStore`
itself: that store is content-addressed (many entries, one per unique
payload, kept for dedup) -- this store exists to keep exactly one thing per
generator (the current baseline, explicitly updated), the opposite shape.

**Scores-first.** The first call to :func:`check_regression` for a
generator with no recorded baseline yet is not a failure -- it is the
measurement that establishes one. The caller records it explicitly via
:meth:`EvalBaselineStore.record_baseline`; nothing here auto-promotes a run
to "the new baseline" without that explicit call.
"""

from __future__ import annotations

from pathlib import Path

from eval_harness.models import EvalScore, RegressionGateOutcome, RegressionGateResult
from requirement_intelligence.run_state.atomic_write import atomic_write_json, read_json_if_valid


class EvalBaselineStore:
    """On-disk store of exactly one current baseline `EvalScore` per
    ``generator_id`` -- ``<store_dir>/<generator_id>.json``.

    A present-but-corrupt baseline file is treated exactly like a missing
    one (:meth:`get_baseline` returns ``None``, never raises) -- mirroring
    `GenerationCacheStore.get`'s own degrade-to-miss invariant.
    """

    def __init__(self, store_dir: Path) -> None:
        self._store_dir = store_dir

    def _path_for(self, generator_id: str) -> Path:
        return self._store_dir / f"{generator_id}.json"

    def get_baseline(self, generator_id: str) -> EvalScore | None:
        raw = read_json_if_valid(self._path_for(generator_id))
        if raw is None:
            return None
        return EvalScore.model_validate(raw)

    def record_baseline(self, generator_id: str, score: EvalScore) -> None:
        """Explicitly set (or replace) ``generator_id``'s current baseline.
        Never called implicitly by :func:`check_regression` -- promoting a
        candidate to the new baseline is always the caller's own decision.
        """
        atomic_write_json(
            self._path_for(generator_id), score.model_dump(mode="json", by_alias=True)
        )


def check_regression(candidate: EvalScore, store: EvalBaselineStore) -> RegressionGateResult:
    """Compare ``candidate`` against ``store``'s current baseline for
    ``candidate.generator_id``.

    - No baseline recorded yet -> ``ESTABLISHED_BASELINE`` (this run IS the
      measurement a baseline would be built from; not a pass or a fail).
    - ``candidate.pass_rate`` below the baseline's -> ``REGRESSED`` -- this
      is the ONLY failure condition, and it is always relative: a low but
      STABLE score never regresses; a high score that DROPPED from an even
      higher baseline does.
    - Otherwise -> ``PASSED`` (stable or improved).
    """
    baseline = store.get_baseline(candidate.generator_id)
    if baseline is None:
        return RegressionGateResult(
            outcome=RegressionGateOutcome.ESTABLISHED_BASELINE,
            candidate_pass_rate=candidate.pass_rate,
            baseline_pass_rate=None,
            reason=(
                f"no prior baseline recorded for generator_id={candidate.generator_id!r}; "
                "this run's own score is available to be recorded as the new baseline"
            ),
        )

    if candidate.pass_rate < baseline.pass_rate:
        return RegressionGateResult(
            outcome=RegressionGateOutcome.REGRESSED,
            candidate_pass_rate=candidate.pass_rate,
            baseline_pass_rate=baseline.pass_rate,
            reason=(
                f"pass rate dropped from baseline {baseline.pass_rate} "
                f"(identity={baseline.identity!r}) to {candidate.pass_rate} "
                f"(identity={candidate.identity!r})"
            ),
        )

    return RegressionGateResult(
        outcome=RegressionGateOutcome.PASSED,
        candidate_pass_rate=candidate.pass_rate,
        baseline_pass_rate=baseline.pass_rate,
        reason="pass rate is stable or improved relative to the recorded baseline",
    )


__all__ = ["EvalBaselineStore", "check_regression"]
