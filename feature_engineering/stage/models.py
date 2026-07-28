"""Structured contracts for stage 14's own persisted state (ADR-0036, ADR-0043 D8).

Distinct from `feature_engineering.generation`/`.cp2`/`.remediation`'s own
models: those describe the outcome of ONE generation/gate/remediation call.
These describe the STAGE's run-scoped, resumable bookkeeping -- one
`FeatureRecord` per `TestableRequirement`, persisted across invocations of
the same run so an unchanged requirement (ADR-0042 Decision 3's own
`content_hash`) is never regenerated, never re-remediated, and its existing
workspace file is left untouched.

This is the Validated Feature Package ADR-0043 D8 names: "per-feature CP2
results... the derived `traceability.json`... and the D5 remediation/
escalation outcomes" -- run-directory-resident, distinct from the untracked
workspace `.feature` files it indexes by relative path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: This package's own contract version -- bumped on a shape change to
#: `FeatureRecord`/`FeatureEngineeringPackage`, independent of
#: `contracts.testable_requirement.CONTRACT_VERSION` (the input contract) and
#: `requirement_intelligence.run_state`'s own `CONTRACT_VERSION` (the run/
#: stage state contract) -- three distinct contracts, never conflated.
CONTRACT_VERSION = "1.0.0"

FEATURE_ENGINEERING_PACKAGE_FILENAME = "feature_engineering_package.json"
FEATURE_ENGINEERING_REPORT_FILENAME = "feature_engineering_report.md"


@dataclass(frozen=True, slots=True)
class FeatureRecord:
    """One `TestableRequirement`'s own generation/CP2/remediation outcome,
    as persisted in the run's Validated Feature Package.

    `feature_path` is relative to `features_root` (POSIX-style, forward
    slashes) so the package is portable across machines/OSes -- never an
    absolute path. It is `None` only for the one case where no content
    exists at all to write: the raw content generator's own output violated
    its tag contract before assembly ever produced text (a
    `FeatureGenerationError` with `content=None` -- see
    `feature_engineering.generation.errors`). This differs from a
    lint-dirty escalation, which always has assembled content and is always
    written to the workspace for human review (ADR-0043 D5's HITL framing).
    """

    requirement_id: str
    content_hash: str
    req_tag: str
    feature_path: str | None
    scn_ids: tuple[str, ...]
    ac_ids_covered: tuple[str, ...]
    cp2_verdict: str
    remediated: bool
    escalated: bool
    escalation_reason: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "requirementId": self.requirement_id,
            "contentHash": self.content_hash,
            "reqTag": self.req_tag,
            "featurePath": self.feature_path,
            "scnIds": list(self.scn_ids),
            "acIdsCovered": list(self.ac_ids_covered),
            "cp2Verdict": self.cp2_verdict,
            "remediated": self.remediated,
            "escalated": self.escalated,
            "escalationReason": self.escalation_reason,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FeatureRecord:
        return cls(
            requirement_id=str(data["requirementId"]),
            content_hash=str(data["contentHash"]),
            req_tag=str(data["reqTag"]),
            feature_path=(str(data["featurePath"]) if data["featurePath"] is not None else None),
            scn_ids=tuple(data.get("scnIds", ())),
            ac_ids_covered=tuple(data.get("acIdsCovered", ())),
            cp2_verdict=str(data["cp2Verdict"]),
            remediated=bool(data["remediated"]),
            escalated=bool(data["escalated"]),
            escalation_reason=(
                str(data["escalationReason"])
                if data.get("escalationReason") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class FeatureEngineeringPackage:
    """The Validated Feature Package's own canonical, persisted record."""

    contract_version: str
    run_id: str
    requirement_set_run_id: str
    generated_at: str
    records: tuple[FeatureRecord, ...]

    @property
    def escalated_records(self) -> tuple[FeatureRecord, ...]:
        return tuple(r for r in self.records if r.escalated)

    def record_for(self, requirement_id: str) -> FeatureRecord | None:
        for record in self.records:
            if record.requirement_id == requirement_id:
                return record
        return None

    def to_json(self) -> dict[str, Any]:
        return {
            "contractVersion": self.contract_version,
            "runId": self.run_id,
            "requirementSetRunId": self.requirement_set_run_id,
            "generatedAt": self.generated_at,
            "records": [r.to_json() for r in self.records],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FeatureEngineeringPackage:
        return cls(
            contract_version=str(data["contractVersion"]),
            run_id=str(data["runId"]),
            requirement_set_run_id=str(data["requirementSetRunId"]),
            generated_at=str(data["generatedAt"]),
            records=tuple(FeatureRecord.from_json(r) for r in data["records"]),
        )


@dataclass(frozen=True, slots=True)
class FeatureEngineeringStageResult:
    """Everything the stage-14 wiring (`.runner.execute_feature_engineering_stage`)
    needs to record the stage's own run-state outcome: every output path
    (workspace `.feature` files plus the run-dir package/report/
    traceability), and whether any requirement escalated (for a future HITL
    surface to read -- not built here)."""

    package: FeatureEngineeringPackage
    package_path: Path
    traceability_path: Path
    report_path: Path
    workspace_feature_paths: tuple[Path, ...]

    @property
    def has_escalations(self) -> bool:
        return bool(self.package.escalated_records)

    @property
    def all_output_paths(self) -> tuple[Path, ...]:
        return (
            self.package_path,
            self.traceability_path,
            self.report_path,
            *self.workspace_feature_paths,
        )


__all__ = [
    "CONTRACT_VERSION",
    "FEATURE_ENGINEERING_PACKAGE_FILENAME",
    "FEATURE_ENGINEERING_REPORT_FILENAME",
    "FeatureEngineeringPackage",
    "FeatureEngineeringStageResult",
    "FeatureRecord",
]
