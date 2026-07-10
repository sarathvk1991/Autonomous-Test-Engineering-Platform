"""OrchestrationPolicy — the declarative rules that govern context composition.

A policy is **data, not behaviour**. It states *what* evidence a context must
contain, *how* candidates rank, *how many* artifacts fit, and *how ties break*.
It does not know how to fetch, group, rank, render, or analyse anything.

Ownership
---------
The policy owns:

* **Coverage rules** — which source categories a context must represent.
* **Ranking rules** — the ordered keys candidate groups are sorted by.
* **Evidence budget** — the bound that keeps a context a context (Invariant 3).
* **Ordering** — how evidence is ordered inside a domain.
* **Selection strategy** — how many groups per category are drawn.
* **Tie-breaking** — the final, total-order key.
* **Explainability** — the template that renders the Orchestration Reason.

The policy explicitly does **not** own execution, connectors, grouping, prompt
rendering, or analysis. It is inert. The Engineering Context Orchestrator
(CAP-076C) is the only component that will ever *apply* it.

Reproducibility (CAP-076A Invariant 7)
--------------------------------------
"No probabilistic ranking shall be permitted" is enforced structurally, not by
convention. :class:`RankingKey` and :class:`TieBreaker` are closed enumerations
of deterministic, total-order keys over values the source data actually carries.
There is no member a probabilistic or model-derived score could be expressed as,
and :class:`RankingRule` additionally rejects duplicate keys and requires a
tie-breaker. A policy that could rank non-deterministically is unrepresentable.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.context_orchestration.models.context_identity import (
    OrchestrationPolicyId,
    PolicyVersion,
)
from requirement_intelligence.models.enums import SourceCategory
from shared.contracts.base import Schema

#: Placeholders an Orchestration Reason template may reference. Any other
#: placeholder is rejected at policy construction, so a reason can never fail to
#: render at orchestration time.
REASON_TEMPLATE_FIELDS: frozenset[str] = frozenset({"subject", "strategy", "groups", "categories"})


class CoverageMode(StrEnum):
    """How much of the available evidence a context is required to represent."""

    ALL_PRESENT_CATEGORIES = "all_present_categories"
    """Every category that produced evidence in the run must be represented.

    This is the rule that repairs the CAP-074B defect: functional, security and
    quality evidence all reach the prompt whenever they exist.
    """

    SINGLE_LARGEST_GROUP = "single_largest_group"
    """Exactly one group is represented — today's behaviour, preserved verbatim.

    Retained so CAP-076C can ship the plumbing with behaviour unchanged and flip
    the policy separately (CAP-076A §9, Stages 3 and 4).
    """


class RankingKey(StrEnum):
    """A deterministic, total-order key that candidate groups are ranked by."""

    RISK_LEVEL_DESC = "risk_level_desc"
    """Most severe rolled-up risk first. A CRITICAL defect outranks 71 code smells."""

    ARTIFACT_COUNT_DESC = "artifact_count_desc"
    """Largest group first. Today's sole ranking key — a ranking by source verbosity."""

    CONSOLIDATED_ID_ASC = "consolidated_id_asc"
    """Lexicographic group id. A total order, so it can terminate any ranking."""


class TieBreaker(StrEnum):
    """The final key applied when every ranking key compares equal.

    Single-member by design. A tie-breaker must be a *total* order over values
    present in the data, and ``consolidated_id`` is the only such value a group
    is guaranteed to carry uniquely. Widening this enum is an ADR-gated change.
    """

    CONSOLIDATED_ID_ASC = "consolidated_id_asc"


class EvidenceOrdering(StrEnum):
    """How evidence is ordered within a single domain section."""

    GROUP_ORDER = "group_order"
    """Preserve the order groups were selected in, and within a group, source order."""

    RISK_THEN_RECORD_ID = "risk_then_record_id"
    """Most severe artifact first; ties broken by ``source_record_id`` ascending."""


class SelectionStrategy(StrEnum):
    """How many groups are drawn, and from where."""

    SINGLE_LARGEST = "single_largest"
    """Take the single top-ranked group overall. Reproduces today's behaviour."""

    COVERAGE_GUARANTEED = "coverage_guaranteed"
    """Take the top-ranked group(s) from every category that produced evidence."""


class CoverageRule(Schema):
    """Which source categories a composed context is required to represent."""

    model_config = ConfigDict(alias_generator=to_camel)

    mode: CoverageMode = Field(...)
    required_categories: tuple[SourceCategory, ...] = Field(
        default=(),
        description=(
            "Categories that must be represented even under SINGLE_LARGEST_GROUP. "
            "Empty means 'whatever the mode implies'."
        ),
    )


class RankingRule(Schema):
    """The ordered ranking keys, terminated by a total-order tie-breaker."""

    model_config = ConfigDict(alias_generator=to_camel)

    keys: tuple[RankingKey, ...] = Field(..., min_length=1)
    tie_breaker: TieBreaker = Field(default=TieBreaker.CONSOLIDATED_ID_ASC)

    @model_validator(mode="after")
    def _validate_total_order(self) -> RankingRule:
        """Reject duplicate keys — a repeated key can never break a tie."""
        if len(set(self.keys)) != len(self.keys):
            raise ValueError(f"Ranking keys must be distinct; got {list(self.keys)!r}.")
        return self


class EvidenceBudget(Schema):
    """The bound that keeps a context small enough for one reasoning session.

    Measured in artifacts rather than tokens: a token budget would couple
    orchestration to a provider's tokenizer, and the policy must stay
    provider-agnostic. CAP-076A §6.3 measured ~5.3k tokens for 71 artifacts, so
    artifact counts are a serviceable proxy.

    Per-domain bounds exist because a global bound alone does not fix the defect:
    with 300 Sonar findings against 4 JIRA issues, a global cap still yields an
    all-Sonar context (CAP-076A risk R8).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    max_artifacts_per_domain: int = Field(..., ge=1)
    max_artifacts_total: int = Field(..., ge=1)

    @model_validator(mode="after")
    def _validate_bounds(self) -> EvidenceBudget:
        """A total below a single domain's cap is unsatisfiable."""
        if self.max_artifacts_total < self.max_artifacts_per_domain:
            raise ValueError(
                f"maxArtifactsTotal ({self.max_artifacts_total}) must be >= "
                f"maxArtifactsPerDomain ({self.max_artifacts_per_domain})."
            )
        return self


class OrchestrationPolicy(Schema):
    """An immutable, declarative, governed rule set for composing one context."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: OrchestrationPolicyId = Field(...)
    policy_version: PolicyVersion = Field(...)
    description: str = Field(..., min_length=1)

    coverage: CoverageRule = Field(...)
    ranking: RankingRule = Field(...)
    evidence_budget: EvidenceBudget = Field(...)
    evidence_ordering: EvidenceOrdering = Field(...)
    selection_strategy: SelectionStrategy = Field(...)

    reason_template: str = Field(
        ...,
        min_length=1,
        description=(
            "Explainability template rendered into the Orchestration Reason. "
            f"May reference only: {sorted(REASON_TEMPLATE_FIELDS)}."
        ),
    )

    @model_validator(mode="after")
    def _validate_policy(self) -> OrchestrationPolicy:
        """Reject policies that are internally inconsistent or cannot render a reason."""
        if (
            self.selection_strategy == SelectionStrategy.COVERAGE_GUARANTEED
            and self.coverage.mode == CoverageMode.SINGLE_LARGEST_GROUP
        ):
            raise ValueError(
                "selectionStrategy 'coverage_guaranteed' contradicts coverage mode "
                "'single_largest_group': a single group cannot guarantee coverage."
            )
        _validate_reason_template(self.reason_template)
        return self

    def render_reason(self, **fields: object) -> str:
        """Render the Orchestration Reason from this policy's template.

        Rendering is the policy's *explainability* responsibility; it is data
        substitution, not orchestration. Every placeholder must be supplied.

        Raises:
            ValueError: If a referenced placeholder was not supplied.
        """
        try:
            return self.reason_template.format(**fields)
        except KeyError as exc:
            raise ValueError(
                f"Orchestration reason template references {exc.args[0]!r}, which was not supplied."
            ) from exc


def _validate_reason_template(template: str) -> None:
    """Reject a reason template referencing an unknown placeholder."""
    from string import Formatter

    referenced = {name for _, name, _, _ in Formatter().parse(template) if name}
    unknown = referenced - REASON_TEMPLATE_FIELDS
    if unknown:
        raise ValueError(
            f"Orchestration reason template references unknown placeholder(s) "
            f"{sorted(unknown)!r}. Allowed: {sorted(REASON_TEMPLATE_FIELDS)!r}."
        )
