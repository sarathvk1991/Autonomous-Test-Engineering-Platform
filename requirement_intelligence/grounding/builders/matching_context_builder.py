"""Builder that translates runtime models into a canonical ``MatchingContext``.

This is the **one place** the Grounding subsystem touches runtime models
(``EngineeringContext``, ``AnalysisResult``, ``SourceArtifact``). It exists so that
no ``GroundingStrategy`` ever depends on them: strategies consume only the canonical
:class:`MatchingContext` / :class:`MatchingRequest` this builder produces.

Construction only — the builder assembles the matching input and does **no**
matching, filtering, scoring, ordering, classification, or mutation. It preserves
the evidence order the orchestrator already fixed (canonical
``functional → security → quality`` domain order) and the requirement order the
response presents. Invalid construction is rejected with
:class:`MatchingContextConstructionError`.

Requirement source
------------------
The generated requirements live in the AI response carried by ``AnalysisResult``.
The builder reads the three governed requirement arrays
(``functional_requirements`` / ``security_requirements`` / ``quality_requirements``)
from the response's strict-JSON body. This deterministic extraction is input
assembly, not normalization: it recovers the requirement strings and their order,
nothing more.
"""

from __future__ import annotations

import json
from typing import Any

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EVIDENCE_DOMAINS,
    EngineeringContext,
)
from requirement_intelligence.grounding.config import GroundingConfiguration
from requirement_intelligence.grounding.identity import GroundedRequirementId
from requirement_intelligence.grounding.models.evidence import EvidenceReference
from requirement_intelligence.grounding.models.matching import (
    MatchingContext,
    MatchingEvidence,
    MatchingRequirement,
)
from requirement_intelligence.models.enums import SourceCategory
from requirement_intelligence.models.source_artifact import SourceArtifact

#: The response arrays that hold generated requirements, mapped to their domain,
#: in canonical domain order. The keys are the governed reasoning-contract fields.
_REQUIREMENT_ARRAYS: tuple[tuple[str, SourceCategory], ...] = (
    ("functional_requirements", SourceCategory.FUNCTIONAL),
    ("security_requirements", SourceCategory.SECURITY),
    ("quality_requirements", SourceCategory.QUALITY),
)


class MatchingContextConstructionError(ValueError):
    """Raised when a ``MatchingContext`` cannot be built from the supplied inputs."""


class MatchingContextBuilder:
    """Assemble a canonical :class:`MatchingContext` from runtime models."""

    def build(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
        configuration: GroundingConfiguration,
    ) -> MatchingContext:
        """Return the canonical matching input for one grounding run.

        Raises:
            MatchingContextConstructionError: If the AI response body is not the
                strict-JSON object the reasoning contract requires.
        """
        evidence = self._evidence(engineering_context)
        requirements = self._requirements(analysis_result)
        return MatchingContext(
            context_id=str(engineering_context.context_id),
            requirements=requirements,
            evidence=evidence,
            configuration=configuration,
            framework_version=configuration.framework_version,
            configuration_version=configuration.version,
        )

    def _evidence(self, engineering_context: EngineeringContext) -> tuple[MatchingEvidence, ...]:
        """Flatten the context's evidence into canonical matching evidence, in order."""
        corpus = engineering_context.evidence
        by_domain = {
            SourceCategory.FUNCTIONAL: corpus.functional_artifacts,
            SourceCategory.SECURITY: corpus.security_artifacts,
            SourceCategory.QUALITY: corpus.quality_artifacts,
        }
        evidence: list[MatchingEvidence] = []
        for domain in EVIDENCE_DOMAINS:
            evidence.extend(_to_matching_evidence(artifact) for artifact in by_domain[domain])
        return tuple(evidence)

    def _requirements(self, analysis_result: AnalysisResult) -> tuple[MatchingRequirement, ...]:
        """Recover the generated requirements from the response body, in order."""
        body = _response_object(analysis_result)
        requirements: list[MatchingRequirement] = []
        for key, domain in _REQUIREMENT_ARRAYS:
            values = body.get(key, [])
            if not isinstance(values, list):
                raise MatchingContextConstructionError(
                    f"Response field '{key}' is not a list of requirements."
                )
            for position, value in enumerate(values):
                if not isinstance(value, str) or not value.strip():
                    continue
                requirements.append(
                    MatchingRequirement(
                        requirement_id=GroundedRequirementId.for_requirement(domain, value),
                        domain=domain,
                        text=value,
                        position=position,
                    )
                )
        return tuple(requirements)


def _to_matching_evidence(artifact: SourceArtifact) -> MatchingEvidence:
    """Reduce one source artifact to its identity and matchable text fields."""
    return MatchingEvidence(
        reference=EvidenceReference(
            source_system=artifact.source_system,
            source_record_id=artifact.source_record_id,
            source_category=artifact.source_category,
            source_type=artifact.source_type,
        ),
        title=artifact.title,
        description=artifact.description,
        tags=tuple(artifact.tags),
        severity=artifact.severity,
        status=artifact.status,
        component=artifact.component,
        location=artifact.location,
    )


def _response_object(analysis_result: AnalysisResult) -> dict[str, Any]:
    """Parse the strict-JSON response body, or reject construction."""
    text = analysis_result.llm_response.generated_text
    try:
        body = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise MatchingContextConstructionError(
            "AI response body is not valid JSON; cannot recover generated requirements."
        ) from exc
    if not isinstance(body, dict):
        raise MatchingContextConstructionError(
            "AI response body is not a JSON object; cannot recover generated requirements."
        )
    return body
