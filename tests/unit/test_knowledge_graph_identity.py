"""Unit tests for the Knowledge Graph Framework typed identities (CAP-084A).

The identities follow the ADR-0015/ADR-0016/ADR-0017/ADR-0018/ADR-0019/ADR-0022
precedent: immutable, string-backed, deterministic value objects that serialise to
and validate from a plain string. No UUIDs, no timestamps, no randomness.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeEdgeVersion,
    KnowledgeFindingId,
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeGraphResultVersion,
    KnowledgeNodeId,
    KnowledgeNodeVersion,
    KnowledgeObservationId,
    KnowledgeObservationVersion,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
    KnowledgeSubgraphId,
)


@pytest.mark.unit
class TestStringIdentifiers:
    def test_valid_policy_id_round_trips(self) -> None:
        pid = KnowledgePolicyId("default-knowledge-graph-policy")
        assert str(pid) == "default-knowledge-graph-policy"
        assert KnowledgePolicyId.parse("  default-knowledge-graph-policy  ") == pid

    @pytest.mark.parametrize("bad", ["", "Upper", "-leading", "trailing-", "has space"])
    def test_invalid_identifier_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            KnowledgePolicyId(bad)

    def test_identifiers_are_frozen(self) -> None:
        pid = KnowledgePolicyId("p")
        with pytest.raises(FrozenInstanceError):
            pid.value = "q"  # type: ignore[misc]

    def test_different_identity_types_are_not_interchangeable(self) -> None:
        # KnowledgeFindingId and KnowledgeObservationId are distinct types even
        # though both are string identifiers with the same shape rules.
        assert KnowledgeFindingId("kf-1") != KnowledgeObservationId("kf-1")


@pytest.mark.unit
class TestDeterministicIds:
    def test_graph_id_is_pure_function_of_dataset(self) -> None:
        a = KnowledgeGraphId.for_dataset("ds-1")
        b = KnowledgeGraphId.for_dataset("ds-1")
        assert a == b
        assert str(a).startswith("kg-")

    def test_graph_id_varies_with_dataset(self) -> None:
        assert KnowledgeGraphId.for_dataset("ds-1") != KnowledgeGraphId.for_dataset("ds-2")

    def test_node_id_is_pure_function_of_inputs(self) -> None:
        a = KnowledgeNodeId.for_entity("requirement", "req-1")
        b = KnowledgeNodeId.for_entity("requirement", "req-1")
        assert a == b
        assert str(a).startswith("kn-")

    def test_node_id_varies_with_node_type(self) -> None:
        assert KnowledgeNodeId.for_entity(
            "requirement", "req-1"
        ) != KnowledgeNodeId.for_entity("module", "req-1")

    def test_node_id_varies_with_referenced_id(self) -> None:
        assert KnowledgeNodeId.for_entity(
            "requirement", "req-1"
        ) != KnowledgeNodeId.for_entity("requirement", "req-2")

    def test_edge_id_is_pure_function_of_inputs(self) -> None:
        a = KnowledgeEdgeId.for_relationship("depends_on", "kn-1", "kn-2")
        b = KnowledgeEdgeId.for_relationship("depends_on", "kn-1", "kn-2")
        assert a == b
        assert str(a).startswith("ke-")

    def test_edge_id_varies_with_edge_type(self) -> None:
        assert KnowledgeEdgeId.for_relationship(
            "depends_on", "kn-1", "kn-2"
        ) != KnowledgeEdgeId.for_relationship("implements", "kn-1", "kn-2")

    def test_edge_id_varies_with_endpoints(self) -> None:
        assert KnowledgeEdgeId.for_relationship(
            "depends_on", "kn-1", "kn-2"
        ) != KnowledgeEdgeId.for_relationship("depends_on", "kn-1", "kn-3")

    def test_edge_id_is_directional(self) -> None:
        """Source/target order matters — a→b is a distinct edge from b→a."""
        assert KnowledgeEdgeId.for_relationship(
            "depends_on", "kn-1", "kn-2"
        ) != KnowledgeEdgeId.for_relationship("depends_on", "kn-2", "kn-1")

    def test_subgraph_id_is_pure_function_of_inputs(self) -> None:
        a = KnowledgeSubgraphId.for_ordinal("kg-1", 0)
        b = KnowledgeSubgraphId.for_ordinal("kg-1", 0)
        assert a == b
        assert str(a).startswith("ks-")

    def test_subgraph_id_varies_with_ordinal(self) -> None:
        assert KnowledgeSubgraphId.for_ordinal("kg-1", 0) != KnowledgeSubgraphId.for_ordinal(
            "kg-1", 1
        )

    def test_observation_id_is_pure_function_of_inputs(self) -> None:
        a = KnowledgeObservationId.for_ordinal("kg-1", 0)
        b = KnowledgeObservationId.for_ordinal("kg-1", 0)
        assert a == b
        assert str(a).startswith("ko-")

    def test_observation_id_varies_with_ordinal(self) -> None:
        assert KnowledgeObservationId.for_ordinal(
            "kg-1", 0
        ) != KnowledgeObservationId.for_ordinal("kg-1", 1)

    def test_finding_id_is_pure_function_of_inputs(self) -> None:
        a = KnowledgeFindingId.for_ordinal("kg-1", 0)
        b = KnowledgeFindingId.for_ordinal("kg-1", 0)
        assert a == b
        assert str(a).startswith("kf-")

    def test_finding_id_varies_with_ordinal(self) -> None:
        assert KnowledgeFindingId.for_ordinal("kg-1", 0) != KnowledgeFindingId.for_ordinal(
            "kg-1", 1
        )

    def test_result_id_is_pure_function_of_graph(self) -> None:
        r = KnowledgeGraphResultId.for_graph("kg-1")
        assert r == KnowledgeGraphResultId.for_graph("kg-1")
        assert str(r).startswith("kgr-")

    def test_result_id_varies_with_graph(self) -> None:
        assert KnowledgeGraphResultId.for_graph("kg-1") != KnowledgeGraphResultId.for_graph(
            "kg-2"
        )

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: KnowledgeGraphId.for_dataset(""),
            lambda: KnowledgeGraphId.for_dataset("   "),
            lambda: KnowledgeNodeId.for_entity("", "req-1"),
            lambda: KnowledgeNodeId.for_entity("requirement", ""),
            lambda: KnowledgeEdgeId.for_relationship("", "kn-1", "kn-2"),
            lambda: KnowledgeEdgeId.for_relationship("depends_on", "", "kn-2"),
            lambda: KnowledgeEdgeId.for_relationship("depends_on", "kn-1", ""),
            lambda: KnowledgeSubgraphId.for_ordinal("", 0),
            lambda: KnowledgeSubgraphId.for_ordinal("kg-1", -1),
            lambda: KnowledgeObservationId.for_ordinal("", 0),
            lambda: KnowledgeObservationId.for_ordinal("kg-1", -1),
            lambda: KnowledgeFindingId.for_ordinal("", 0),
            lambda: KnowledgeFindingId.for_ordinal("kg-1", -1),
            lambda: KnowledgeGraphResultId.for_graph(""),
            lambda: KnowledgeGraphResultId.for_graph("   "),
        ],
    )
    def test_invalid_inputs_rejected(self, factory) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError):
            factory()


@pytest.mark.unit
class TestSemanticVersions:
    def test_parse_and_str_round_trip(self) -> None:
        assert str(KnowledgeGraphFrameworkVersion.parse("1.2.3")) == "1.2.3"

    def test_versions_are_ordered(self) -> None:
        assert KnowledgePolicyVersion(1, 0, 0) < KnowledgePolicyVersion(1, 1, 0)

    def test_compatibility_is_major_only(self) -> None:
        assert KnowledgePolicyVersion(1, 4, 0).is_compatible_with(
            KnowledgePolicyVersion(1, 0, 9)
        )
        assert not KnowledgePolicyVersion(2, 0, 0).is_compatible_with(
            KnowledgePolicyVersion(1, 0, 0)
        )

    @pytest.mark.parametrize("bad", ["1.0", "x.y.z", "-1.0.0"])
    def test_invalid_version_string_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            KnowledgeGraphFrameworkVersion.parse(bad)

    def test_negative_components_rejected(self) -> None:
        with pytest.raises(ValueError):
            KnowledgeGraphResultVersion(1, -1, 0)

    def test_the_six_version_axes_are_distinct_types(self) -> None:
        # Framework, policy, node-schema, edge-schema, observation-schema, and
        # result-contract versions evolve independently; they are distinct types.
        types = {
            KnowledgeGraphFrameworkVersion,
            KnowledgePolicyVersion,
            KnowledgeNodeVersion,
            KnowledgeEdgeVersion,
            KnowledgeObservationVersion,
            KnowledgeGraphResultVersion,
        }
        assert len(types) == 6


@pytest.mark.unit
class TestPydanticSerialization:
    def test_identity_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            pid: KnowledgePolicyId
            ver: KnowledgePolicyVersion

        m = M(pid=KnowledgePolicyId("p"), ver=KnowledgePolicyVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"pid": "p", "ver": "1.0.0"}
        assert M.model_validate({"pid": "p", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises_validation_error(self) -> None:
        class M(BaseModel):
            pid: KnowledgePolicyId

        with pytest.raises(ValidationError):
            M.model_validate({"pid": "Bad Id"})

    def test_result_id_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            rid: KnowledgeGraphResultId

        m = M(rid=KnowledgeGraphResultId.for_graph("kg-1"))
        dumped = m.model_dump(mode="json")
        assert dumped["rid"] == str(KnowledgeGraphResultId.for_graph("kg-1"))
        assert M.model_validate(dumped) == m
