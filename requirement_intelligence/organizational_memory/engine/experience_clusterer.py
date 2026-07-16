"""Deterministic experience clustering (CAP-085B).

``ExperienceClusterer`` is the **sole clustering authority**: it is the only
component that groups :class:`Experience` instances together. It consumes
**Experiences only** (ADR-0027 §D12) — never the two Layer 2 results
``ExperienceCollector`` was built from, and never a Lesson or Best Practice.

Clustering is **deterministic equality only** — experiences that share the
same governed source layer and byte-identical description text are grouped
together; nothing else. This is never semantic similarity, never fuzzy
matching, never an embedding, never a probabilistic judgement (Stage 4 of the
CAP-085B brief). A cluster never mixes Continuous Improvement and Knowledge
Graph experiences (OM-CLU-002).
"""

from __future__ import annotations

from collections import defaultdict

from requirement_intelligence.organizational_memory.models.experience import Experience


class ExperienceClusterer:
    """Group Experiences by deterministic equality. No semantic similarity."""

    def cluster(self, experiences: tuple[Experience, ...]) -> tuple[tuple[Experience, ...], ...]:
        """Deterministically group *experiences* by (source_layer, description) equality.

        Returns clusters in a stable order: sorted by the cluster's own sorted
        experience-id tuple, so the same input always yields the same
        cluster ordering regardless of the input tuple's own order.
        """
        groups: dict[tuple[str, str], list[Experience]] = defaultdict(list)
        for experience in experiences:
            key = (str(experience.source_layer), experience.description)
            groups[key].append(experience)

        clusters = [
            tuple(sorted(group, key=lambda e: str(e.experience_id))) for group in groups.values()
        ]
        clusters.sort(key=lambda cluster: tuple(str(e.experience_id) for e in cluster))
        return tuple(clusters)
