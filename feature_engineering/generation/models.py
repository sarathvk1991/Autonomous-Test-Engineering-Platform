"""The Layer 2 generation core's structured output contract.

Two future, NOT-built-here milestones consume this:

* CP2's deterministic gate (ADR-0040 / ADR-0043 D5) will read
  ``lint_result`` and ``acceptance_criteria_coverage`` to decide pass/fail —
  this core only *computes* both; it never gates on them (D5's own framing:
  compute the coverage check here, gate on it there).
* Run-state wiring (ADR-0036 stage 14) will read ``file_path`` and
  ``requirement_id`` to record the stage's artifact and decide, on a later
  run, whether ``content_hash`` still matches (the SKIP predicate) —
  ``build_generated_feature`` never writes to disk or to ``run_state.json``
  itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from feature_engineering.gherkin_lint.models import LintResult


@dataclass(frozen=True, slots=True)
class ScenarioAssignment:
    """One scenario's platform-assigned identity within the assembled feature."""

    #: The scenario's own name, exactly as generated.
    name: str
    #: The real, content-addressed @SCN-* id minted for this scenario.
    scn_id: str
    #: Every real @AC-* id this scenario carries, in tag order.
    ac_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeneratedFeature:
    """The fully assembled, validated output of one generation call."""

    #: The originating requirement's own platform-assigned id.
    requirement_id: str
    #: The complete, validated .feature file text.
    content: str
    #: The deterministic target path this content would be written to.
    file_path: Path
    #: The Feature-level tag the platform attached (e.g. "@REQ-a1b2c3d4").
    req_tag: str
    #: One entry per generated scenario, in AST order.
    scenarios: tuple[ScenarioAssignment, ...]
    #: Every input AC-* id mapped to whether >=1 scenario carries it.
    #: CP2's future coverage gate reads this; it is computed, never gated,
    #: here (ADR-0043 D5).
    acceptance_criteria_coverage: dict[str, bool]
    #: The full 17-rule result against the assembled content. Always clean
    #: for a `GeneratedFeature` that was actually returned — a dirty result
    #: is raised as a FeatureGenerationError, never returned successfully.
    lint_result: LintResult

    @property
    def fully_covered(self) -> bool:
        """True when every acceptance criterion maps to >=1 scenario."""
        return all(self.acceptance_criteria_coverage.values())
