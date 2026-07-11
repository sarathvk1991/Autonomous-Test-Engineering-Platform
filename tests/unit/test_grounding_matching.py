"""Unit tests for the canonical matching models and the MatchingContextBuilder.

These pin the contract every future GroundingStrategy consumes: construction,
immutability, version consistency, deterministic equality, the pure
``to_requests`` fan-out, and the builder that translates runtime models into a
``MatchingContext`` (the one boundary that touches ``EngineeringContext`` /
``AnalysisResult``). No matching, scoring, or classification is exercised.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration import (
    DefaultOrchestrationPolicy,
    EngineeringContextBuilder,
    EngineeringContextOrchestrator,
)
from requirement_intelligence.grounding import (
    GroundingStrategy,
    MatchingContext,
    MatchingContextBuilder,
    MatchingContextConstructionError,
    MatchingEvidence,
    MatchingRequest,
    MatchingRequirement,
)
from requirement_intelligence.grounding.config import default_grounding_configuration
from requirement_intelligence.grounding.identity import (
    GroundedRequirementId,
    GroundingFrameworkVersion,
)
from requirement_intelligence.grounding.models.evidence import EvidenceReference
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact
from requirement_intelligence.platform import PlatformContext
from shared.enums.base import ProviderType

_RESPONSE_JSON = (
    '{"summary": "s", '
    '"functional_requirements": ["Display the inventory after login.", "Lock the account."], '
    '"security_requirements": ["Set the nosniff header."], '
    '"quality_requirements": [], '
    '"risks": [], "recommendations": []}'
)


def _artifact(index: int, category: SourceCategory, source_type: SourceType) -> SourceArtifact:
    return SourceArtifact(
        artifact_id=f"A{index}",
        source_system=SourceSystem.JIRA,
        source_record_id=f"REC-{index:03d}",
        source_category=category,
        source_type=source_type,
        title=f"Artifact {index}",
        description=f"Body {index}",
        tags=["t1"],
    )


def _engineering_context() -> object:
    group = ConsolidatedArtifact(
        consolidated_id="cons-component-auth",
        module="auth",
        risk_level=RiskLevel.LOW,
        consolidation_reason="Grouped by component auth",
        functional_artifacts=[
            _artifact(0, SourceCategory.FUNCTIONAL, SourceType.STORY),
            _artifact(1, SourceCategory.FUNCTIONAL, SourceType.STORY),
        ],
        security_artifacts=[_artifact(100, SourceCategory.SECURITY, SourceType.DAST)],
        quality_artifacts=[],
    )
    orchestrator = EngineeringContextOrchestrator(
        policy=DefaultOrchestrationPolicy(),
        builder=EngineeringContextBuilder(),
    )
    return orchestrator.orchestrate([group]).context


def _analysis_result(generated_text: str = _RESPONSE_JSON) -> AnalysisResult:
    from requirement_intelligence.llm.llm_models import LLMResponse

    now = datetime(2026, 7, 11, tzinfo=UTC)
    return AnalysisResult(
        analysis_id="a-1",
        execution_id="e-1",
        source_consolidated_id="cons-component-auth",
        prompt_version="1.0.0",
        reasoning_contract_version="1.0.0",
        provider=ProviderType.GEMINI,
        model="gemini-stub",
        started_at=now,
        completed_at=now,
        duration_ms=1.0,
        llm_response=LLMResponse(
            provider=ProviderType.GEMINI, model="gemini-stub", generated_text=generated_text
        ),
    )


@pytest.mark.unit
class TestMatchingModels:
    def _evidence(self) -> MatchingEvidence:
        return MatchingEvidence(
            reference=EvidenceReference(
                source_system=SourceSystem.OWASP_ZAP,
                source_record_id="10021",
                source_category=SourceCategory.SECURITY,
                source_type=SourceType.DAST,
            ),
            title="X-Content-Type-Options Header Missing",
            tags=("header",),
        )

    def _requirement(self) -> MatchingRequirement:
        text = "Set the nosniff header."
        return MatchingRequirement(
            requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, text),
            domain=SourceCategory.SECURITY,
            text=text,
            position=0,
        )

    def _context(self) -> MatchingContext:
        config = default_grounding_configuration()
        return MatchingContext(
            context_id="ctx-auth-abc",
            requirements=(self._requirement(),),
            evidence=(self._evidence(),),
            configuration=config,
            framework_version=config.framework_version,
            configuration_version=config.version,
        )

    def test_context_constructs_and_is_immutable(self) -> None:
        ctx = self._context()
        assert ctx.context_id == "ctx-auth-abc"
        with pytest.raises(ValidationError):
            ctx.context_id = "other"  # type: ignore[misc]

    def test_context_rejects_version_mismatch(self) -> None:
        config = default_grounding_configuration()
        with pytest.raises(ValidationError):
            MatchingContext(
                context_id="ctx",
                requirements=(),
                evidence=(),
                configuration=config,
                framework_version=GroundingFrameworkVersion(9, 9, 9),
                configuration_version=config.version,
            )

    def test_to_requests_is_a_pure_fan_out(self) -> None:
        ctx = self._context()
        requests = ctx.to_requests()
        assert len(requests) == len(ctx.requirements)
        assert all(isinstance(r, MatchingRequest) for r in requests)
        assert requests[0].requirement == ctx.requirements[0]
        assert requests[0].evidence == ctx.evidence
        assert requests[0].context_id == ctx.context_id

    def test_deterministic_equality(self) -> None:
        assert self._context() == self._context()

    def test_serialises_camel_case_and_round_trips(self) -> None:
        ctx = self._context()
        dumped = ctx.model_dump(mode="json", by_alias=True)
        assert "contextId" in dumped
        assert MatchingContext.model_validate(dumped) == ctx


@pytest.mark.unit
class TestMatchingContextBuilder:
    def test_builds_evidence_in_canonical_domain_order(self) -> None:
        ctx = MatchingContextBuilder().build(
            _engineering_context(), _analysis_result(), default_grounding_configuration()
        )
        # Two functional artifacts precede the one security artifact.
        categories = [str(e.reference.source_category) for e in ctx.evidence]
        assert categories == ["functional", "functional", "security"]

    def test_recovers_requirements_with_positions_and_ids(self) -> None:
        ctx = MatchingContextBuilder().build(
            _engineering_context(), _analysis_result(), default_grounding_configuration()
        )
        assert [r.text for r in ctx.requirements] == [
            "Display the inventory after login.",
            "Lock the account.",
            "Set the nosniff header.",
        ]
        assert [str(r.domain) for r in ctx.requirements] == [
            "functional",
            "functional",
            "security",
        ]
        assert [r.position for r in ctx.requirements] == [0, 1, 0]
        first = ctx.requirements[0]
        assert first.requirement_id == GroundedRequirementId.for_requirement(
            SourceCategory.FUNCTIONAL, "Display the inventory after login."
        )

    def test_build_is_deterministic(self) -> None:
        engineering_context = _engineering_context()
        config = default_grounding_configuration()
        one = MatchingContextBuilder().build(engineering_context, _analysis_result(), config)
        two = MatchingContextBuilder().build(engineering_context, _analysis_result(), config)
        assert one == two

    def test_rejects_non_json_response(self) -> None:
        with pytest.raises(MatchingContextConstructionError):
            MatchingContextBuilder().build(
                _engineering_context(),
                _analysis_result("not json at all"),
                default_grounding_configuration(),
            )

    def test_rejects_non_object_response(self) -> None:
        with pytest.raises(MatchingContextConstructionError):
            MatchingContextBuilder().build(
                _engineering_context(),
                _analysis_result("[1, 2, 3]"),
                default_grounding_configuration(),
            )


@pytest.mark.unit
class TestStrategyContractAndRegistration:
    def test_strategy_match_consumes_a_matching_request(self) -> None:
        params = list(inspect.signature(GroundingStrategy.match).parameters)
        assert params == ["self", "request"]

    def test_platform_context_registers_builder(self) -> None:
        builder = PlatformContext().create_matching_context_builder()
        assert isinstance(builder, MatchingContextBuilder)
