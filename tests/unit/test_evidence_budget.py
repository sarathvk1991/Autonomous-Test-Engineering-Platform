"""CAP-076D — deterministic evidence-budget allocation and evidence ordering.

Both units are pure functions, and both are load-bearing for the milestone's
central guarantee: the same candidates always yield the same context. They are
tested directly, away from the orchestrator, because a bug in either would show
up downstream as "the reasoner saw slightly different evidence" — the hardest
class of defect to notice.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.context_orchestration import (
    ContextOrchestrationError,
    EvidenceBudget,
    EvidenceOrdering,
    allocate_evidence_budget,
    order_evidence,
)
from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact

FUNCTIONAL = SourceCategory.FUNCTIONAL
SECURITY = SourceCategory.SECURITY
QUALITY = SourceCategory.QUALITY


def _budget(per_domain: int, total: int) -> EvidenceBudget:
    return EvidenceBudget(max_artifacts_per_domain=per_domain, max_artifacts_total=total)


def _allocate(
    per_domain: int, total: int, functional: int, security: int, quality: int
) -> tuple[int, int, int]:
    allocation = allocate_evidence_budget(
        _budget(per_domain, total),
        {FUNCTIONAL: functional, SECURITY: security, QUALITY: quality},
    )
    return (allocation[FUNCTIONAL], allocation[SECURITY], allocation[QUALITY])


# ---------------------------------------------------------------------------
# Allocation — the uncontested case
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_a_domain_is_never_allocated_more_than_it_can_supply() -> None:
    """Allocating budget to evidence that does not exist would strand it."""
    assert _allocate(25, 60, functional=2, security=0, quality=3) == (2, 0, 3)


@pytest.mark.unit
def test_each_domain_takes_its_cap_when_the_caps_fit_the_total() -> None:
    """25 + 25 + 25 exceeds 60, but 4 + 25 + 25 does not: nothing is contested."""
    assert _allocate(25, 60, functional=4, security=83, quality=300) == (4, 25, 25)


@pytest.mark.unit
def test_the_per_domain_cap_binds_before_the_total_does() -> None:
    assert _allocate(10, 100, functional=50, security=50, quality=50) == (10, 10, 10)


# ---------------------------------------------------------------------------
# Allocation — the contested case (water-filling)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_a_contested_total_is_split_equally_between_the_contenders() -> None:
    """Max-min fairness: no domain is starved so another can be verbose."""
    assert _allocate(25, 60, functional=100, security=100, quality=100) == (20, 20, 20)


@pytest.mark.unit
def test_a_domain_that_wants_less_than_its_share_releases_the_surplus() -> None:
    """Functional needs 2; the 58 it did not use is split between the other two."""
    assert _allocate(50, 60, functional=2, security=100, quality=100) == (2, 29, 29)


@pytest.mark.unit
def test_a_verbose_domain_cannot_crowd_out_a_sparse_one() -> None:
    """The CAP-076A R8 risk: 300 Sonar findings against 4 JIRA issues."""
    assert _allocate(25, 30, functional=4, security=83, quality=300) == (4, 13, 13)


@pytest.mark.unit
def test_an_indivisible_remainder_is_granted_one_unit_at_a_time() -> None:
    """10 across three equal contenders: 3 each, and the last unit to the first domain."""
    assert _allocate(10, 10, functional=25, security=25, quality=25) == (4, 3, 3)


@pytest.mark.unit
def test_only_domains_with_evidence_contest_the_budget() -> None:
    """An empty domain does not take a share the others could have spent."""
    assert _allocate(10, 10, functional=0, security=25, quality=25) == (0, 5, 5)


@pytest.mark.unit
def test_a_total_below_the_number_of_contenders_is_shared_rather_than_hoarded() -> None:
    """Two units, three contenders: one each, in canonical order, never both to one."""
    assert _allocate(2, 2, functional=5, security=5, quality=5) == (1, 1, 0)


@pytest.mark.unit
def test_allocation_never_exceeds_either_bound() -> None:
    for total in range(9, 40):
        allocation = _allocate(9, total, functional=30, security=30, quality=30)
        assert sum(allocation) <= total
        assert all(value <= 9 for value in allocation)


@pytest.mark.unit
def test_allocation_is_reproducible() -> None:
    first = _allocate(25, 60, functional=7, security=83, quality=300)
    second = _allocate(25, 60, functional=7, security=83, quality=300)
    assert first == second


@pytest.mark.unit
def test_every_domain_is_present_in_the_allocation() -> None:
    """A domain that supplies nothing is allocated zero, never omitted."""
    allocation = allocate_evidence_budget(_budget(5, 10), {QUALITY: 3})
    assert set(allocation) == {FUNCTIONAL, SECURITY, QUALITY}
    assert allocation[FUNCTIONAL] == 0


@pytest.mark.unit
def test_negative_availability_is_rejected() -> None:
    with pytest.raises(ContextOrchestrationError, match="cannot be negative"):
        allocate_evidence_budget(_budget(5, 10), {QUALITY: -1})


# ---------------------------------------------------------------------------
# Evidence ordering
# ---------------------------------------------------------------------------


def _artifact(record_id: str, severity: str | None = None) -> SourceArtifact:
    return SourceArtifact(
        artifact_id=f"art-{record_id}",
        source_system=SourceSystem.SONARQUBE,
        source_record_id=record_id,
        source_category=QUALITY,
        source_type=SourceType.SAST,
        title=f"Finding {record_id}",
        severity=severity,
    )


@pytest.mark.unit
def test_group_order_preserves_the_supplied_sequence() -> None:
    artifacts = [_artifact("C"), _artifact("A"), _artifact("B")]
    ordered = order_evidence(EvidenceOrdering.GROUP_ORDER, artifacts)
    assert [a.source_record_id for a in ordered] == ["C", "A", "B"]


@pytest.mark.unit
def test_risk_then_record_id_places_the_most_severe_first() -> None:
    artifacts = [
        _artifact("A", "Low"),
        _artifact("B", "Blocker"),
        _artifact("C", "Major"),
    ]
    ordered = order_evidence(EvidenceOrdering.RISK_THEN_RECORD_ID, artifacts)
    assert [a.source_record_id for a in ordered] == ["B", "C", "A"]


@pytest.mark.unit
def test_risk_then_record_id_breaks_ties_on_record_id_ascending() -> None:
    artifacts = [_artifact("Z", "High"), _artifact("A", "High")]
    ordered = order_evidence(EvidenceOrdering.RISK_THEN_RECORD_ID, artifacts)
    assert [a.source_record_id for a in ordered] == ["A", "Z"]


@pytest.mark.unit
def test_an_artifact_without_a_severity_is_ordered_as_low_risk() -> None:
    """``artifact_risk`` defaults to LOW, so a group always has a well-defined order."""
    artifacts = [_artifact("A"), _artifact("B", "Critical")]
    ordered = order_evidence(EvidenceOrdering.RISK_THEN_RECORD_ID, artifacts)
    assert [a.source_record_id for a in ordered] == ["B", "A"]


@pytest.mark.unit
def test_ordering_is_reproducible() -> None:
    artifacts = [_artifact("B", "High"), _artifact("A", "High"), _artifact("C", "Low")]
    first = order_evidence(EvidenceOrdering.RISK_THEN_RECORD_ID, artifacts)
    second = order_evidence(EvidenceOrdering.RISK_THEN_RECORD_ID, list(reversed(artifacts)))
    assert [a.source_record_id for a in first] == [a.source_record_id for a in second]


@pytest.mark.unit
def test_an_unimplemented_ordering_raises() -> None:
    with pytest.raises(ContextOrchestrationError, match="not implemented"):
        order_evidence("alphabetical", [_artifact("A")])  # type: ignore[arg-type]
