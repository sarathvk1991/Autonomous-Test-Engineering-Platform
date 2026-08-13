"""Structured contracts for stage 15's own persisted state (ADR-0036, ADR-0044).

Mirrors :mod:`feature_engineering.stage.models` deliberately -- one
``AssetRecord`` per generation/reuse-engine need (step-definition or
test-data), persisted in the run directory as the Validated Automation
Package, the same "per-need bookkeeping distinct from the subsystems' own
per-call outcome shapes" split stage 14's own ``FeatureRecord`` already
establishes for the Validated Feature Package.

ADR-0044 D1 names the Validated Automation Package's contents: "step
definitions, page objects, utility classes, Java test-data classes... an
automation coverage report, a CP3 validation report, and a CP4 validation
report." This module's ``AutomationEngineeringPackage`` is the first of
those (per-asset outcomes); ``cp3_report.json``/``cp4_report.json``
(:mod:`.runner`) are the latter two, written as separate artifacts exactly
as D1 names them separately, not folded into one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from requirement_intelligence.llm.generation_identity import GenerationIdentity

#: This package's own contract version -- independent of
#: `feature_engineering.stage.models.CONTRACT_VERSION` (the Validated
#: Feature Package's own, separate contract) and
#: `requirement_intelligence.run_state`'s own run/stage state contract.
CONTRACT_VERSION = "1.0.0"

AUTOMATION_ENGINEERING_PACKAGE_FILENAME = "automation_engineering_package.json"
CP3_REPORT_FILENAME = "cp3_report.json"
CP4_REPORT_FILENAME = "cp4_report.json"
PROMOTION_REPORT_FILENAME = "promotion_report.json"
AUTOMATION_ENGINEERING_REPORT_FILENAME = "automation_engineering_report.md"


@dataclass(frozen=True, slots=True)
class AssetRecord:
    """One Gherkin step-need's or test-data specification's own generation/
    reuse/promotion outcome, as persisted in the run's Validated Automation
    Package.

    ``need_kind`` is ``"step_definition"`` or ``"test_data"`` -- the two
    asset kinds this stage's initial wiring actually derives needs for (see
    this package's own report: page-object/utility needs have no existing
    per-step derivation from raw Gherkin text, the same class of gap as
    step captures, so no page-object/utility ``AssetRecord`` is ever
    produced here -- one may only ever appear nested inside a step
    definition's own generation via ``page_object_request``/
    ``utility_request``, neither supplied by this wiring).

    ``outcome`` is one of ``"generated"``/``"bound"``/``"escalated"`` (the
    reuse engine's own exhaustive vocabulary, ADR-0044 D3/D4) -- always
    ``"generated"`` for test-data (ADR-0044 D7: spec-driven, no reuse
    decision at all). ``promotion_status`` is populated only for a
    ``"generated"`` step-definition outcome (test-data classes are
    structurally excluded from promotion, ADR-0044 D7 --
    :func:`automation_engineering.promotion.outcomes.promote_outcome`'s own
    type signature does not accept a ``GeneratedTestDataClass``); ``None``
    for ``"bound"`` (nothing to promote) and for ``"escalated"`` (nothing
    was generated to promote either).

    ``generation_identity`` (additive, the re-run/delta-scoped-regeneration
    cluster's own pinning foundation -- `docs/architecture/
    mentor-feedback-scoping.md` item #1's re-run item) is the prompt/model
    identity that produced this record's own generated content, threaded
    from the generator's own already-captured `LLMResponse`/`PromptDefinition`
    identity (never re-derived). Populated only for an ``outcome ==
    "generated"`` record -- the same "identity exists only where an LLM call
    actually happened" scoping ``workspace_path`` already uses -- ``None``
    for ``"bound"`` (no LLM call, reused from the catalog) and
    ``"escalated"`` (no successful generation). Purely additive persistence:
    it is not consumed by any cache, gate, or skip logic anywhere in this
    module.
    """

    need_text: str
    need_kind: str
    outcome: str
    class_name: str | None = None
    target_package: str | None = None
    workspace_path: str | None = None
    escalated: bool = False
    escalation_check: str | None = None
    escalation_reason: str | None = None
    promotion_status: str | None = None
    promotion_detail: str | None = None
    promoted_path: str | None = None
    generation_identity: GenerationIdentity | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "needText": self.need_text,
            "needKind": self.need_kind,
            "outcome": self.outcome,
            "className": self.class_name,
            "targetPackage": self.target_package,
            "workspacePath": self.workspace_path,
            "escalated": self.escalated,
            "escalationCheck": self.escalation_check,
            "escalationReason": self.escalation_reason,
            "promotionStatus": self.promotion_status,
            "promotionDetail": self.promotion_detail,
            "promotedPath": self.promoted_path,
            "generationIdentity": (
                self.generation_identity.model_dump(mode="json", by_alias=True)
                if self.generation_identity is not None
                else None
            ),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> AssetRecord:
        return cls(
            need_text=str(data["needText"]),
            need_kind=str(data["needKind"]),
            outcome=str(data["outcome"]),
            class_name=(str(data["className"]) if data.get("className") is not None else None),
            target_package=(
                str(data["targetPackage"]) if data.get("targetPackage") is not None else None
            ),
            workspace_path=(
                str(data["workspacePath"]) if data.get("workspacePath") is not None else None
            ),
            escalated=bool(data.get("escalated", False)),
            escalation_check=(
                str(data["escalationCheck"]) if data.get("escalationCheck") is not None else None
            ),
            escalation_reason=(
                str(data["escalationReason"])
                if data.get("escalationReason") is not None
                else None
            ),
            promotion_status=(
                str(data["promotionStatus"]) if data.get("promotionStatus") is not None else None
            ),
            promotion_detail=(
                str(data["promotionDetail"]) if data.get("promotionDetail") is not None else None
            ),
            promoted_path=(
                str(data["promotedPath"]) if data.get("promotedPath") is not None else None
            ),
            generation_identity=(
                GenerationIdentity.model_validate(data["generationIdentity"])
                if data.get("generationIdentity") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class AutomationEngineeringPackage:
    """The Validated Automation Package's own canonical, persisted record
    of every asset need this run resolved (generate/bind/escalate) --
    mirrors :class:`feature_engineering.stage.models.FeatureEngineeringPackage`.
    """

    contract_version: str
    run_id: str
    feature_engineering_run_id: str
    generated_at: str
    records: tuple[AssetRecord, ...]

    @property
    def escalated_records(self) -> tuple[AssetRecord, ...]:
        return tuple(r for r in self.records if r.escalated)

    def to_json(self) -> dict[str, Any]:
        return {
            "contractVersion": self.contract_version,
            "runId": self.run_id,
            "featureEngineeringRunId": self.feature_engineering_run_id,
            "generatedAt": self.generated_at,
            "records": [r.to_json() for r in self.records],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> AutomationEngineeringPackage:
        return cls(
            contract_version=str(data["contractVersion"]),
            run_id=str(data["runId"]),
            feature_engineering_run_id=str(data["featureEngineeringRunId"]),
            generated_at=str(data["generatedAt"]),
            records=tuple(AssetRecord.from_json(r) for r in data["records"]),
        )


@dataclass(frozen=True, slots=True)
class AutomationEngineeringStageResult:
    """Everything the stage-15 wiring (`.runner.execute_automation_engineering_stage`)
    needs to record the stage's own run-state outcome."""

    package: AutomationEngineeringPackage
    package_path: Path
    cp3_report_path: Path
    cp4_report_path: Path
    promotion_report_path: Path
    report_path: Path
    workspace_java_paths: tuple[Path, ...]
    promoted_baseline_paths: tuple[Path, ...]
    cp3_passed: bool
    cp4_passed: bool

    @property
    def has_escalations(self) -> bool:
        return bool(self.package.escalated_records)

    @property
    def all_output_paths(self) -> tuple[Path, ...]:
        return (
            self.package_path,
            self.cp3_report_path,
            self.cp4_report_path,
            self.promotion_report_path,
            self.report_path,
            *self.workspace_java_paths,
        )


__all__ = [
    "AUTOMATION_ENGINEERING_PACKAGE_FILENAME",
    "AUTOMATION_ENGINEERING_REPORT_FILENAME",
    "CONTRACT_VERSION",
    "CP3_REPORT_FILENAME",
    "CP4_REPORT_FILENAME",
    "PROMOTION_REPORT_FILENAME",
    "AssetRecord",
    "AutomationEngineeringPackage",
    "AutomationEngineeringStageResult",
]
