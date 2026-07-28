"""Human-readable rendering of one stage run's Validated Feature Package.

Pure projection, mirroring every other Layer 1 `*_report.md` builder's own
posture (`cp1_report_builder.py`, `quality_governance` serializer, etc.):
this module computes no verdict and re-evaluates nothing -- it renders
`FeatureEngineeringPackage.records` exactly as the stage already decided.
"""

from __future__ import annotations

from feature_engineering.stage.models import FeatureEngineeringPackage


def build_report(package: FeatureEngineeringPackage) -> str:
    lines = [
        "# Feature Engineering Report (Stage 14)",
        "",
        f"Run: {package.run_id}",
        f"Requirements processed: {len(package.records)}",
        f"Escalations: {len(package.escalated_records)}",
        "",
        "| Requirement | CP2 Verdict | Remediated | Escalated | Feature Path |",
        "|---|---|---|---|---|",
    ]
    for record in package.records:
        lines.append(
            f"| {record.requirement_id} | {record.cp2_verdict} | {record.remediated} "
            f"| {record.escalated} | {record.feature_path or '(none)'} |"
        )
    if package.escalated_records:
        lines += ["", "## Escalations (human-in-the-loop)", ""]
        for record in package.escalated_records:
            lines.append(f"- **{record.requirement_id}**: {record.escalation_reason}")
    return "\n".join(lines) + "\n"


__all__ = ["build_report"]
