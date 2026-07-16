"""Architecture-only tests for the governed :class:`OrganizationalMemoryPolicy`
(CAP-085A, ADR-0027).

Covers the builder, the default policy, capability switches, and threshold
validation. No algorithm reads this policy yet — it is data only (Stage 5 of
ADR-0027's brief).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
)
from requirement_intelligence.organizational_memory.policy import (
    DEFAULT_ORGANIZATIONAL_MEMORY_POLICY_ID,
    OrganizationalMemoryCapabilitySwitches,
    OrganizationalMemoryPolicy,
    OrganizationalMemoryPolicyBuilder,
    OrganizationalMemoryThresholds,
    default_organizational_memory_policy,
)


@pytest.mark.unit
class TestOrganizationalMemoryCapabilitySwitches:
    def test_defaults_enable_the_four_governed_capabilities(self) -> None:
        switches = OrganizationalMemoryCapabilitySwitches()
        assert switches.enable_experience_capture is True
        assert switches.enable_lesson_promotion is True
        assert switches.enable_best_practice_promotion is True
        assert switches.enable_retirement is True

    def test_defaults_reserve_every_future_engine_family_off(self) -> None:
        switches = OrganizationalMemoryCapabilitySwitches()
        assert switches.enable_deterministic_engine is False
        assert switches.enable_ml_engine is False
        assert switches.enable_llm_engine is False
        assert switches.enable_graph_rag_engine is False
        assert switches.enable_neuro_symbolic_engine is False

    def test_is_immutable(self) -> None:
        switches = OrganizationalMemoryCapabilitySwitches()
        with pytest.raises(ValidationError):
            switches.enable_lesson_promotion = False  # type: ignore[misc]

    def test_round_trips(self) -> None:
        switches = OrganizationalMemoryCapabilitySwitches()
        dumped = switches.model_dump(mode="json", by_alias=True)
        assert OrganizationalMemoryCapabilitySwitches.model_validate(dumped) == switches


@pytest.mark.unit
class TestOrganizationalMemoryThresholds:
    def _thresholds(self, **overrides: object) -> OrganizationalMemoryThresholds:
        defaults: dict[str, object] = dict(
            minimum_experiences_for_lesson=3,
            minimum_lessons_for_best_practice=2,
            minimum_confidence_for_best_practice=3,
        )
        defaults.update(overrides)
        return OrganizationalMemoryThresholds(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_bounds(self) -> None:
        thresholds = self._thresholds()
        assert thresholds.minimum_experiences_for_lesson == 3

    def test_rejects_zero_minimum_experiences(self) -> None:
        with pytest.raises(ValidationError):
            self._thresholds(minimum_experiences_for_lesson=0)

    def test_rejects_zero_minimum_lessons(self) -> None:
        with pytest.raises(ValidationError):
            self._thresholds(minimum_lessons_for_best_practice=0)

    def test_rejects_confidence_ordinal_out_of_bounds(self) -> None:
        with pytest.raises(ValidationError):
            self._thresholds(minimum_confidence_for_best_practice=4)

    def test_accepts_confidence_ordinal_zero(self) -> None:
        thresholds = self._thresholds(minimum_confidence_for_best_practice=0)
        assert thresholds.minimum_confidence_for_best_practice == 0

    def test_is_immutable(self) -> None:
        thresholds = self._thresholds()
        with pytest.raises(ValidationError):
            thresholds.minimum_experiences_for_lesson = 10  # type: ignore[misc]


@pytest.mark.unit
class TestOrganizationalMemoryPolicy:
    def test_constructs_with_governed_fields(self) -> None:
        policy = OrganizationalMemoryPolicy(
            policy_id=OrganizationalMemoryPolicyId("test-policy"),
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
            description="A test policy.",
            capability_switches=OrganizationalMemoryCapabilitySwitches(),
            thresholds=OrganizationalMemoryThresholds(
                minimum_experiences_for_lesson=1,
                minimum_lessons_for_best_practice=1,
                minimum_confidence_for_best_practice=0,
            ),
        )
        assert policy.policy_id == OrganizationalMemoryPolicyId("test-policy")

    def test_rejects_empty_description(self) -> None:
        with pytest.raises(ValidationError):
            OrganizationalMemoryPolicy(
                policy_id=OrganizationalMemoryPolicyId("test-policy"),
                policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
                description="",
                capability_switches=OrganizationalMemoryCapabilitySwitches(),
                thresholds=OrganizationalMemoryThresholds(
                    minimum_experiences_for_lesson=1,
                    minimum_lessons_for_best_practice=1,
                    minimum_confidence_for_best_practice=0,
                ),
            )

    def test_is_immutable(self) -> None:
        policy = default_organizational_memory_policy()
        with pytest.raises(ValidationError):
            policy.description = "mutated"  # type: ignore[misc]


@pytest.mark.unit
class TestOrganizationalMemoryPolicyBuilder:
    def test_builds_the_default_policy(self) -> None:
        policy = OrganizationalMemoryPolicyBuilder().build()
        assert policy.policy_id == DEFAULT_ORGANIZATIONAL_MEMORY_POLICY_ID

    def test_default_policy_version_is_1_0_0(self) -> None:
        policy = OrganizationalMemoryPolicyBuilder().build()
        assert str(policy.policy_version) == "1.0.0"

    def test_default_policy_deterministic_engine_is_reserved_off(self) -> None:
        policy = OrganizationalMemoryPolicyBuilder().build()
        assert policy.capability_switches.enable_deterministic_engine is False

    def test_default_policy_curation_switches_are_on(self) -> None:
        policy = OrganizationalMemoryPolicyBuilder().build()
        assert policy.capability_switches.enable_experience_capture is True
        assert policy.capability_switches.enable_lesson_promotion is True
        assert policy.capability_switches.enable_best_practice_promotion is True
        assert policy.capability_switches.enable_retirement is True

    def test_module_level_helper_matches_builder(self) -> None:
        assert default_organizational_memory_policy() == OrganizationalMemoryPolicyBuilder().build()

    def test_repeated_calls_return_equal_but_independent_policies(self) -> None:
        a = default_organizational_memory_policy()
        b = default_organizational_memory_policy()
        assert a == b
        assert a is not b
