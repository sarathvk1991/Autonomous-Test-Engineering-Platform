"""The orchestrator's hand-off to the builder: what each group contributed.

:class:`GroupContribution` is the value the Engineering Context Orchestrator
produces once every decision is made — the group, the rank it achieved, how many
of its artifacts survived the evidence budget in each domain, and the reason it
was admitted. The builder turns it into a
:class:`~...models.engineering_context.ContextContribution`.

Why counts rather than artifacts
--------------------------------
The artifacts themselves travel separately, as one already-ordered
:class:`~...models.engineering_context.ContextEvidence`. A domain's evidence is
ordered *across* the contributing groups (the most severe finding first,
whichever group produced it), so no group owns a contiguous slice of it and
handing the builder per-group artifact lists would invite it to concatenate them
back into the wrong order. The builder never reorders evidence; giving it nothing
to reorder is how that guarantee is kept structurally rather than by convention.

This is a plain frozen dataclass, not a ``Schema``: it is internal transport
between two collaborators in one subsystem and is never serialised. The
serialised record is ``ContextContribution``.
"""

from __future__ import annotations

from dataclasses import dataclass

from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact


@dataclass(frozen=True)
class GroupContribution:
    """One consolidation group's post-budget contribution to a context."""

    group: ConsolidatedArtifact
    rank: int
    inclusion_reason: str
    functional_count: int = 0
    security_count: int = 0
    quality_count: int = 0

    @property
    def consolidated_id(self) -> str:
        """The contributing group's identifier."""
        return self.group.consolidated_id

    @property
    def contributed_count(self) -> int:
        """Artifacts this group contributed, across all three domains."""
        return self.functional_count + self.security_count + self.quality_count

    @property
    def candidate_count(self) -> int:
        """Artifacts this group carries, across all three domains."""
        return (
            len(self.group.functional_artifacts)
            + len(self.group.security_artifacts)
            + len(self.group.quality_artifacts)
        )

    @property
    def truncated(self) -> bool:
        """The evidence budget admitted only part of what this group carries."""
        return self.contributed_count < self.candidate_count

    @classmethod
    def whole(
        cls, group: ConsolidatedArtifact, rank: int, inclusion_reason: str
    ) -> GroupContribution:
        """A contribution of every artifact the group carries — nothing truncated.

        This is what ``single_largest`` selection always produces, and what
        ``coverage_guaranteed`` produces for any group that fits inside its
        domains' remaining budget.
        """
        return cls(
            group=group,
            rank=rank,
            inclusion_reason=inclusion_reason,
            functional_count=len(group.functional_artifacts),
            security_count=len(group.security_artifacts),
            quality_count=len(group.quality_artifacts),
        )
