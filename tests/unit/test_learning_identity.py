"""Architecture-only tests for the Learning Framework's typed identity value
objects (CAP-086A, ADR-0029).

Covers determinism (pure functions of their inputs, no UUID, no clock),
round-trip string parsing, version-axis independence, and rejection of
malformed inputs. No behaviour is exercised — no candidate is proposed, no
learning is validated, no engine runs.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.learning.identity import (
    LearningCandidateId,
    LearningConfidenceId,
    LearningFrameworkVersion,
    LearningId,
    LearningLifecycleId,
    LearningLifecycleVersion,
    LearningPolicyId,
    LearningPolicyVersion,
    LearningResultId,
    LearningResultVersion,
    LearningValidationId,
    LearningValidationVersion,
    LearningVersion,
)


@pytest.mark.unit
class TestLearningPolicyId:
    def test_accepts_a_valid_lowercase_identifier(self) -> None:
        assert str(LearningPolicyId("default-learning-policy")) == "default-learning-policy"

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError):
            LearningPolicyId("")

    def test_rejects_uppercase(self) -> None:
        with pytest.raises(ValueError):
            LearningPolicyId("Default-Policy")

    def test_parse_strips_whitespace(self) -> None:
        assert str(LearningPolicyId.parse("  policy-1  ")) == "policy-1"


@pytest.mark.unit
class TestLearningResultId:
    def test_for_source_is_deterministic(self) -> None:
        a = LearningResultId.for_source("omr-1")
        b = LearningResultId.for_source("omr-1")
        assert a == b

    def test_for_source_differs_by_source(self) -> None:
        a = LearningResultId.for_source("omr-1")
        b = LearningResultId.for_source("omr-2")
        assert a != b

    def test_for_source_rejects_empty_source(self) -> None:
        with pytest.raises(ValueError):
            LearningResultId.for_source("")

    def test_for_source_produces_the_lr_prefix(self) -> None:
        assert str(LearningResultId.for_source("omr-1")).startswith("lr-")

    def test_for_source_is_a_single_argument_factory(self) -> None:
        """Learning consumes exactly one input (ADR-0028 §Stage 12) — unlike
        OrganizationalMemoryId.for_inputs, this factory takes one id, never two."""
        import inspect

        signature = inspect.signature(LearningResultId.for_source)
        params = [p for p in signature.parameters if p != "cls"]
        assert params == ["organizational_memory_result_id"]


@pytest.mark.unit
class TestLearningCandidateId:
    def test_for_source_is_deterministic(self) -> None:
        a = LearningCandidateId.for_source("bp-1")
        b = LearningCandidateId.for_source("bp-1")
        assert a == b

    def test_for_source_differs_by_source(self) -> None:
        a = LearningCandidateId.for_source("bp-1")
        b = LearningCandidateId.for_source("bp-2")
        assert a != b

    def test_for_source_rejects_empty_source(self) -> None:
        with pytest.raises(ValueError):
            LearningCandidateId.for_source("")

    def test_for_source_produces_the_lc_prefix(self) -> None:
        assert str(LearningCandidateId.for_source("bp-1")).startswith("lc-")


_ORDINAL_ID_CLASSES = (LearningId, LearningValidationId, LearningConfidenceId, LearningLifecycleId)


@pytest.mark.unit
class TestOrdinalMintedIdentities:
    """LearningId, LearningValidationId, LearningConfidenceId, and
    LearningLifecycleId all share the ``for_ordinal``
    pure-function-of-ordinal pattern."""

    @pytest.mark.parametrize(
        "id_class,prefix",
        [
            (LearningId, "lg-"),
            (LearningValidationId, "lv-"),
            (LearningConfidenceId, "lf-"),
            (LearningLifecycleId, "ll-"),
        ],
    )
    def test_for_ordinal_is_deterministic(self, id_class: type, prefix: str) -> None:
        a = id_class.for_ordinal("lr-test", 0)
        b = id_class.for_ordinal("lr-test", 0)
        assert a == b
        assert str(a).startswith(prefix)

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_differs_by_ordinal(self, id_class: type) -> None:
        a = id_class.for_ordinal("lr-test", 0)
        b = id_class.for_ordinal("lr-test", 1)
        assert a != b

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_differs_by_seed_id(self, id_class: type) -> None:
        a = id_class.for_ordinal("lr-a", 0)
        b = id_class.for_ordinal("lr-b", 0)
        assert a != b

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_rejects_empty_seed_id(self, id_class: type) -> None:
        with pytest.raises(ValueError):
            id_class.for_ordinal("", 0)

    @pytest.mark.parametrize("id_class", _ORDINAL_ID_CLASSES)
    def test_for_ordinal_rejects_negative_ordinal(self, id_class: type) -> None:
        with pytest.raises(ValueError):
            id_class.for_ordinal("lr-test", -1)


@pytest.mark.unit
class TestVersionAxisIndependence:
    def test_all_six_version_types_are_distinct(self) -> None:
        axes = (
            LearningFrameworkVersion,
            LearningPolicyVersion,
            LearningVersion,
            LearningLifecycleVersion,
            LearningValidationVersion,
            LearningResultVersion,
        )
        assert len(set(axes)) == 6

    def test_no_version_type_subclasses_another(self) -> None:
        axes = (
            LearningFrameworkVersion,
            LearningPolicyVersion,
            LearningVersion,
            LearningLifecycleVersion,
            LearningValidationVersion,
            LearningResultVersion,
        )
        for outer in axes:
            for inner in axes:
                if outer is inner:
                    continue
                assert not issubclass(outer, inner)

    def test_version_parses_from_semver_string(self) -> None:
        assert LearningResultVersion.parse("1.2.3") == LearningResultVersion(1, 2, 3)

    def test_version_rejects_malformed_string(self) -> None:
        with pytest.raises(ValueError):
            LearningFrameworkVersion.parse("not-a-version")

    def test_version_rejects_negative_components(self) -> None:
        with pytest.raises(ValueError):
            LearningPolicyVersion(-1, 0, 0)

    def test_version_str_round_trips(self) -> None:
        version = LearningResultVersion(2, 3, 4)
        assert str(version) == "2.3.4"
        assert LearningResultVersion.parse(str(version)) == version

    def test_is_compatible_with_checks_major_only(self) -> None:
        a = LearningFrameworkVersion(1, 0, 0)
        b = LearningFrameworkVersion(1, 5, 2)
        c = LearningFrameworkVersion(2, 0, 0)
        assert a.is_compatible_with(b)
        assert not a.is_compatible_with(c)
