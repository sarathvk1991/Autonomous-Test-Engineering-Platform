"""Architecture-only tests for the Organizational Memory Framework's typed
identity value objects (CAP-085A, ADR-0027).

Covers determinism (pure functions of their inputs, no UUID, no clock),
round-trip string parsing, version-axis independence, and rejection of
malformed inputs. No behaviour is exercised — no experience is captured, no
lesson is promoted, no engine runs.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    BestPracticeVersion,
    ExperienceId,
    KnowledgeLifecycleId,
    KnowledgeLifecycleVersion,
    KnowledgePromotionId,
    LessonId,
    LessonVersion,
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
    OrganizationalMemoryResultId,
    OrganizationalMemoryResultVersion,
)


@pytest.mark.unit
class TestOrganizationalMemoryPolicyId:
    def test_accepts_a_valid_lowercase_identifier(self) -> None:
        assert str(OrganizationalMemoryPolicyId("default-organizational-memory-policy")) == (
            "default-organizational-memory-policy"
        )

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError):
            OrganizationalMemoryPolicyId("")

    def test_rejects_uppercase(self) -> None:
        with pytest.raises(ValueError):
            OrganizationalMemoryPolicyId("Default-Policy")

    def test_parse_strips_whitespace(self) -> None:
        assert str(OrganizationalMemoryPolicyId.parse("  policy-1  ")) == "policy-1"


@pytest.mark.unit
class TestOrganizationalMemoryId:
    def test_for_inputs_is_deterministic(self) -> None:
        a = OrganizationalMemoryId.for_inputs("ci-1", "kg-1")
        b = OrganizationalMemoryId.for_inputs("ci-1", "kg-1")
        assert a == b

    def test_for_inputs_differs_by_continuous_improvement_result_id(self) -> None:
        a = OrganizationalMemoryId.for_inputs("ci-1", "kg-1")
        b = OrganizationalMemoryId.for_inputs("ci-2", "kg-1")
        assert a != b

    def test_for_inputs_differs_by_knowledge_graph_result_id(self) -> None:
        a = OrganizationalMemoryId.for_inputs("ci-1", "kg-1")
        b = OrganizationalMemoryId.for_inputs("ci-1", "kg-2")
        assert a != b

    def test_for_inputs_rejects_empty_continuous_improvement_result_id(self) -> None:
        with pytest.raises(ValueError):
            OrganizationalMemoryId.for_inputs("", "kg-1")

    def test_for_inputs_rejects_empty_knowledge_graph_result_id(self) -> None:
        with pytest.raises(ValueError):
            OrganizationalMemoryId.for_inputs("ci-1", "")

    def test_for_inputs_produces_the_om_prefix(self) -> None:
        assert str(OrganizationalMemoryId.for_inputs("ci-1", "kg-1")).startswith("om-")


@pytest.mark.unit
class TestExperienceId:
    def test_for_source_is_deterministic(self) -> None:
        a = ExperienceId.for_source("continuous_improvement", "imp-finding-1")
        b = ExperienceId.for_source("continuous_improvement", "imp-finding-1")
        assert a == b

    def test_for_source_differs_by_layer(self) -> None:
        a = ExperienceId.for_source("continuous_improvement", "ref-1")
        b = ExperienceId.for_source("knowledge_graph", "ref-1")
        assert a != b

    def test_for_source_differs_by_reference(self) -> None:
        a = ExperienceId.for_source("knowledge_graph", "ref-1")
        b = ExperienceId.for_source("knowledge_graph", "ref-2")
        assert a != b

    def test_for_source_rejects_empty_layer(self) -> None:
        with pytest.raises(ValueError):
            ExperienceId.for_source("", "ref-1")

    def test_for_source_rejects_empty_reference(self) -> None:
        with pytest.raises(ValueError):
            ExperienceId.for_source("knowledge_graph", "")

    def test_for_source_produces_the_ex_prefix(self) -> None:
        assert str(ExperienceId.for_source("knowledge_graph", "ref-1")).startswith("ex-")


_ORDINAL_ID_CLASSES = (LessonId, BestPracticeId, KnowledgePromotionId, KnowledgeLifecycleId)


@pytest.mark.unit
class TestOrdinalMintedIdentities:
    """LessonId, BestPracticeId, KnowledgePromotionId, KnowledgeLifecycleId,
    and OrganizationalMemoryResultId all share the ``for_ordinal``/``for_memory``
    pure-function-of-ordinal pattern."""

    @pytest.mark.parametrize(
        "id_class,prefix",
        [
            (LessonId, "ls-"),
            (BestPracticeId, "bp-"),
            (KnowledgePromotionId, "kp-"),
            (KnowledgeLifecycleId, "kl-"),
        ],
    )
    def test_for_ordinal_is_deterministic(self, id_class: type, prefix: str) -> None:
        a = id_class.for_ordinal("om-test", 0)
        b = id_class.for_ordinal("om-test", 0)
        assert a == b
        assert str(a).startswith(prefix)

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_differs_by_ordinal(self, id_class: type) -> None:
        a = id_class.for_ordinal("om-test", 0)
        b = id_class.for_ordinal("om-test", 1)
        assert a != b

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_differs_by_memory_id(self, id_class: type) -> None:
        a = id_class.for_ordinal("om-a", 0)
        b = id_class.for_ordinal("om-b", 0)
        assert a != b

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_rejects_empty_memory_id(self, id_class: type) -> None:
        with pytest.raises(ValueError):
            id_class.for_ordinal("", 0)

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_rejects_negative_ordinal(self, id_class: type) -> None:
        with pytest.raises(ValueError):
            id_class.for_ordinal("om-test", -1)

    def test_result_id_for_memory_is_deterministic(self) -> None:
        a = OrganizationalMemoryResultId.for_memory("om-test")
        b = OrganizationalMemoryResultId.for_memory("om-test")
        assert a == b
        assert str(a).startswith("omr-")

    def test_result_id_for_memory_differs_by_memory_id(self) -> None:
        a = OrganizationalMemoryResultId.for_memory("om-a")
        b = OrganizationalMemoryResultId.for_memory("om-b")
        assert a != b

    def test_result_id_for_memory_rejects_empty_memory_id(self) -> None:
        with pytest.raises(ValueError):
            OrganizationalMemoryResultId.for_memory("")


@pytest.mark.unit
class TestVersionAxisIndependence:
    def test_all_six_version_types_are_distinct(self) -> None:
        axes = (
            OrganizationalMemoryFrameworkVersion,
            OrganizationalMemoryPolicyVersion,
            LessonVersion,
            BestPracticeVersion,
            KnowledgeLifecycleVersion,
            OrganizationalMemoryResultVersion,
        )
        assert len(set(axes)) == 6

    def test_no_version_type_subclasses_another(self) -> None:
        axes = (
            OrganizationalMemoryFrameworkVersion,
            OrganizationalMemoryPolicyVersion,
            LessonVersion,
            BestPracticeVersion,
            KnowledgeLifecycleVersion,
            OrganizationalMemoryResultVersion,
        )
        for outer in axes:
            for inner in axes:
                if outer is inner:
                    continue
                assert not issubclass(outer, inner)

    def test_version_parses_from_semver_string(self) -> None:
        assert OrganizationalMemoryResultVersion.parse("1.2.3") == (
            OrganizationalMemoryResultVersion(1, 2, 3)
        )

    def test_version_rejects_malformed_string(self) -> None:
        with pytest.raises(ValueError):
            OrganizationalMemoryFrameworkVersion.parse("not-a-version")

    def test_version_rejects_negative_components(self) -> None:
        with pytest.raises(ValueError):
            OrganizationalMemoryPolicyVersion(-1, 0, 0)

    def test_version_str_round_trips(self) -> None:
        version = OrganizationalMemoryResultVersion(2, 3, 4)
        assert str(version) == "2.3.4"
        assert OrganizationalMemoryResultVersion.parse(str(version)) == version

    def test_is_compatible_with_checks_major_only(self) -> None:
        a = OrganizationalMemoryFrameworkVersion(1, 0, 0)
        b = OrganizationalMemoryFrameworkVersion(1, 5, 2)
        c = OrganizationalMemoryFrameworkVersion(2, 0, 0)
        assert a.is_compatible_with(b)
        assert not a.is_compatible_with(c)
