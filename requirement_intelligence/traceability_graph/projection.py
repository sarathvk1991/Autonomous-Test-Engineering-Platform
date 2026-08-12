"""Deterministic requirement -> scenario -> step projection.

The sole node/edge authority for the Traceability Graph — the minimal slice
(mentor item #3's traceability graph, `requirement -> scenario -> step`
only; page-object and execution-result hops are explicitly deferred, see
`docs/architecture/mentor-feedback-scoping.md` item #3's "GRAPHS DESIGN
SURFACED" note).

Reads two already-real, already-produced artifacts — it synthesizes
nothing (unlike ADR-0023's own default historical-dataset provider, which
SHA-256-synthesizes fake ids for lack of a real Historical Dataset; see
that same note for why this build does not go through the Knowledge
Graph subsystem's own runtime service at all):

* `TestableRequirementSet` (L1, `contracts.testable_requirement`) — the full
  universe of requirements this run produced. A requirement with no
  corresponding `FeatureRecord`, or one whose record produced no feature
  content, or whose `.feature` file carries no `@SCN-*` tag, still gets a
  REQUIREMENT node — it is exactly the "requirement with no test" case the
  completeness report exists to name.
* `FeatureEngineeringPackage` (L2, `feature_engineering.stage.models`) — one
  `FeatureRecord` per requirement, naming its own `.feature` file's path
  (relative to `features_root`).

Scenario/step extraction re-parses each `.feature` file with the SAME
parser CP2/CP3/`traceability.json` already use
(`feature_engineering.gherkin_lint.parse_source_text`) — never a second
Gherkin parser — and reads `@SCN-*` tags the identical way
`feature_engineering.stage.traceability.build_traceability_index` already
does (a scenario's own tags union the feature's own tags), because the
`.feature` file is the authoritative source, never the package's own
bookkeeping (mirrors that module's own stated principle). A scenario with
no `@SCN-*` tag is silently excluded, exactly as `build_traceability_index`
already excludes it from `traceability.json`.

No LLM, no inference beyond the tag matching `build_traceability_index`
already proves out. Deterministic: the same requirement set + feature
package + files on disk always produce the identical graph.
"""

from __future__ import annotations

import re
from pathlib import Path

from contracts.testable_requirement import TestableRequirementSet
from feature_engineering.gherkin_lint import parse_source_text
from feature_engineering.stage.models import FeatureEngineeringPackage
from requirement_intelligence.traceability_graph.identity import (
    edge_id_for,
    graph_id_for,
    node_id_for,
)
from requirement_intelligence.traceability_graph.models import (
    TraceabilityEdge,
    TraceabilityEdgeType,
    TraceabilityGraph,
    TraceabilityNode,
    TraceabilityNodeType,
)

_SCN_TAG_RE = re.compile(r"^@SCN-\S+$")


def project_traceability_graph(
    requirement_set: TestableRequirementSet,
    feature_package: FeatureEngineeringPackage,
    *,
    features_root: Path,
) -> TraceabilityGraph:
    """Project requirement -> scenario -> step into a deterministic graph.

    Every requirement in *requirement_set* gets a node, regardless of
    whether it has any downstream scenario/step content — that absence is
    the signal `completeness.evaluate_completeness` reports on.
    """
    nodes: dict[str, TraceabilityNode] = {}
    edges: dict[str, TraceabilityEdge] = {}

    def _add_node(node_type: TraceabilityNodeType, referenced_id: str, label: str) -> str:
        node_id = node_id_for(node_type.value, referenced_id)
        if node_id not in nodes:
            nodes[node_id] = TraceabilityNode(
                node_id=node_id, node_type=node_type, referenced_id=referenced_id, label=label
            )
        return node_id

    def _add_edge(
        edge_type: TraceabilityEdgeType, source_id: str, target_id: str, rationale: str
    ) -> None:
        edge_id = edge_id_for(edge_type.value, source_id, target_id)
        if edge_id not in edges:
            edges[edge_id] = TraceabilityEdge(
                edge_id=edge_id,
                edge_type=edge_type,
                source_node_id=source_id,
                target_node_id=target_id,
                rationale=rationale,
            )

    for requirement in requirement_set.requirements:
        requirement_node_id = _add_node(
            TraceabilityNodeType.REQUIREMENT,
            requirement.requirement_id,
            f"Requirement {requirement.requirement_id}",
        )

        record = feature_package.record_for(requirement.requirement_id)
        if record is None or record.feature_path is None:
            continue
        path = features_root / record.feature_path
        if not path.exists():
            continue

        source = parse_source_text(path.read_text(encoding="utf-8"), path=record.feature_path)
        if source.feature is None:
            continue

        feature_tags = {tag["name"] for tag in source.feature.get("tags", [])}
        for child in source.feature.get("children", []):
            scenario = child.get("scenario")
            if not scenario:
                continue
            own_tags = {tag["name"] for tag in scenario.get("tags", [])}
            effective_tags = own_tags | feature_tags
            scn_ids = sorted(t.removeprefix("@") for t in effective_tags if _SCN_TAG_RE.match(t))
            if not scn_ids:
                continue

            steps = scenario.get("steps", [])
            for scn_id in scn_ids:
                scenario_node_id = _add_node(
                    TraceabilityNodeType.SCENARIO, scn_id, scenario.get("name") or scn_id
                )
                _add_edge(
                    TraceabilityEdgeType.HAS_SCENARIO,
                    requirement_node_id,
                    scenario_node_id,
                    f"Requirement {requirement.requirement_id} has scenario {scn_id}.",
                )
                for ordinal, step in enumerate(steps):
                    step_referenced_id = f"{scn_id}::step-{ordinal:03d}"
                    step_text = step.get("text") or step_referenced_id
                    step_node_id = _add_node(
                        TraceabilityNodeType.STEP, step_referenced_id, step_text
                    )
                    _add_edge(
                        TraceabilityEdgeType.HAS_STEP,
                        scenario_node_id,
                        step_node_id,
                        f"Scenario {scn_id} has step {ordinal + 1}.",
                    )

    graph_id = graph_id_for(requirement_set.run_id)
    return TraceabilityGraph(
        graph_id=graph_id, nodes=tuple(nodes.values()), edges=tuple(edges.values())
    )


__all__ = ["project_traceability_graph"]
