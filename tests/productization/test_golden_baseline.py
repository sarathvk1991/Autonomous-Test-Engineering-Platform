"""CAP-070 — Golden End-to-End Validation Baseline.

Productization tests that validate the complete Requirement Intelligence pipeline
against a deterministic golden dataset.  Every subsystem must execute; every
governed artifact must be generated; manifests must be internally consistent;
and two consecutive pipeline runs must produce identical findings and verdicts
(excluding run-specific provenance such as IDs and timestamps).

Test organisation
-----------------
Phase 3  — Pipeline execution  (every subsystem fires)
Phase 4  — Output verification (artifacts, manifest, cross-references, checksums)
Phase 5  — Determinism         (run twice; compare content, not provenance)
Phase 6  — Productization assertions (structured per-layer contract checks)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from requirement_intelligence.models.enums import SourceCategory
from requirement_intelligence.normalization.models.normalization_result import NormalizationResult
from requirement_intelligence.validation.models.validation_enums import ValidationVerdict
from tests.productization.conftest import PipelineResult, _run_golden_pipeline
from tests.productization.fixtures.golden_dataset import (
    EXPECTED_CONSOLIDATED_COUNT,
    EXPECTED_FUNCTIONAL_REQUIREMENTS_COUNT,
    EXPECTED_MODULE,
    EXPECTED_QUALITY_REQUIREMENTS_COUNT,
    EXPECTED_RECOMMENDATIONS_COUNT,
    EXPECTED_RISKS_COUNT,
    EXPECTED_SECURITY_REQUIREMENTS_COUNT,
    GOLDEN_DATASET_VERSION,
    GOLDEN_SOURCE_ARTIFACTS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CORE_ARTIFACTS = frozenset(
    {
        "consolidated_artifact.json",
        "engineering_context.json",
        "prompt.txt",
        "llm_request.json",
    }
)
_RESULT_ARTIFACTS = frozenset(
    {
        "analysis_result.json",
        "raw_llm_response.json",
        "execution_summary.md",
        "baseline_metrics.md",
        "review.md",
    }
)
_VALIDATION_ARTIFACTS = frozenset({"validation_result.json", "validation_report.md"})
_CP1_ARTIFACTS = frozenset({"cp1_report.md"})
_ALL_ARTIFACTS = (
    _CORE_ARTIFACTS | _RESULT_ARTIFACTS | _VALIDATION_ARTIFACTS | _CP1_ARTIFACTS | {"manifest.json"}
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parsed_response_structure(result: PipelineResult) -> dict:
    """Extract the deterministic structure from the normalization result."""
    pr = result.normalization_result.parsed_response
    if pr is None:
        return {}
    normalized = pr.normalized_structure
    if normalized is None:
        return {}
    return dict(normalized)


# ===========================================================================
# PHASE 3 — Pipeline Execution
# ===========================================================================


class TestPhase3PipelineExecution:
    """Every subsystem in the governed pipeline must execute successfully."""

    @pytest.mark.productization
    def test_source_artifacts_loaded(self, golden_pipeline_result: PipelineResult) -> None:
        """All nine golden source artifacts are loaded."""
        assert golden_pipeline_result.source_artifact_count == len(GOLDEN_SOURCE_ARTIFACTS)
        assert golden_pipeline_result.source_artifact_count == 9

    @pytest.mark.productization
    def test_consolidation_produces_single_group(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """All artifacts share component='authentication' → one ConsolidatedArtifact."""
        assert len(golden_pipeline_result.consolidated_artifacts) == EXPECTED_CONSOLIDATED_COUNT

    @pytest.mark.productization
    def test_consolidated_artifact_module(self, golden_pipeline_result: PipelineResult) -> None:
        """The consolidated module name matches the golden dataset's component."""
        assert golden_pipeline_result.selected.module == EXPECTED_MODULE

    @pytest.mark.productization
    def test_consolidated_artifact_has_all_categories(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The consolidated artifact carries functional, security, and quality artifacts."""
        selected = golden_pipeline_result.selected
        assert len(selected.functional_artifacts) > 0, "Expected functional artifacts"
        assert len(selected.security_artifacts) > 0, "Expected security artifacts"
        assert len(selected.quality_artifacts) > 0, "Expected quality artifacts"

    @pytest.mark.productization
    def test_consolidated_functional_count(self, golden_pipeline_result: PipelineResult) -> None:
        """Four JIRA functional artifacts (1 epic + 3 stories)."""
        assert len(golden_pipeline_result.selected.functional_artifacts) == 4

    @pytest.mark.productization
    def test_consolidated_security_count(self, golden_pipeline_result: PipelineResult) -> None:
        """Three OWASP ZAP security artifacts."""
        assert len(golden_pipeline_result.selected.security_artifacts) == 3

    @pytest.mark.productization
    def test_consolidated_quality_count(self, golden_pipeline_result: PipelineResult) -> None:
        """Two SonarQube quality artifacts."""
        assert len(golden_pipeline_result.selected.quality_artifacts) == 2

    @pytest.mark.productization
    def test_orchestrator_produced_an_engineering_context(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """EngineeringContextOrchestrator produced the context the prompt was built from."""
        assert golden_pipeline_result.engineering_context is not None

    @pytest.mark.productization
    def test_default_orchestration_policy_is_active(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """CAP-076D: the runtime executes DefaultOrchestrationPolicy."""
        orchestration = golden_pipeline_result.engineering_context.orchestration
        assert str(orchestration.policy_id) == "coverage"
        assert str(orchestration.policy_version) == "1.0.0"

    @pytest.mark.productization
    def test_context_draws_on_the_only_group_the_golden_dataset_produces(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The golden dataset consolidates to one group, so one group contributes."""
        provenance = golden_pipeline_result.engineering_context.provenance
        assert provenance.contributing_group_count == 1
        assert provenance.contributing_consolidated_ids == (
            golden_pipeline_result.selected.consolidated_id,
        )

    @pytest.mark.productization
    def test_context_carries_every_artifact_of_the_contributing_group(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Nothing is dropped: the whole group fits inside the policy's budget.

        Compared as multisets, not sequences — the active policy orders evidence by
        risk, so a positional comparison would test the ordering rule rather than
        the completeness claim this test makes. Ordering is tested separately.
        """
        selected = golden_pipeline_result.selected
        evidence = golden_pipeline_result.engineering_context.evidence
        assert sorted(a.source_record_id for a in evidence.functional_artifacts) == sorted(
            a.source_record_id for a in selected.functional_artifacts
        )
        assert sorted(a.source_record_id for a in evidence.security_artifacts) == sorted(
            a.source_record_id for a in selected.security_artifacts
        )
        assert sorted(a.source_record_id for a in evidence.quality_artifacts) == sorted(
            a.source_record_id for a in selected.quality_artifacts
        )

    @pytest.mark.productization
    def test_all_three_evidence_domains_reach_the_reasoner(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The CAP-074B repair, asserted against the golden baseline."""
        coverage = golden_pipeline_result.engineering_context.coverage
        assert coverage.all_present_categories_represented is True
        assert coverage.rule_satisfied is True
        assert [str(c) for c in coverage.represented_categories] == [
            "functional",
            "security",
            "quality",
        ]

    @pytest.mark.productization
    def test_active_policy_orders_evidence_by_risk_then_record_id(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The ordering rule is the one behaviour the golden dataset can isolate."""
        from requirement_intelligence.consolidation.consolidation_rules import artifact_risk

        rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        security = golden_pipeline_result.engineering_context.evidence.security_artifacts
        keys = [(-rank[str(artifact_risk(a))], a.source_record_id) for a in security]
        assert keys == sorted(keys)

    @pytest.mark.productization
    def test_the_evidence_budget_did_not_bind_this_dataset(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Nine artifacts sit far inside a 25-per-domain budget; nothing was truncated."""
        budget = golden_pipeline_result.engineering_context.evidence_budget
        assert budget.truncated is False
        assert budget.total_used == 9

    @pytest.mark.productization
    def test_analysis_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """RequirementAnalysisService produced an AnalysisResult."""
        assert golden_pipeline_result.analysis_result is not None

    @pytest.mark.productization
    def test_analysis_result_has_llm_response(self, golden_pipeline_result: PipelineResult) -> None:
        """AnalysisResult carries the stub provider's LLMResponse."""
        assert golden_pipeline_result.analysis_result.llm_response is not None
        assert golden_pipeline_result.analysis_result.llm_response.generated_text != ""

    @pytest.mark.productization
    def test_normalization_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """ResponseNormalizer produced a NormalizationResult."""
        assert isinstance(golden_pipeline_result.normalization_result, NormalizationResult)

    @pytest.mark.productization
    def test_normalization_produced_parsed_response(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """NormalizationResult carries a populated ParsedResponse."""
        assert golden_pipeline_result.normalization_result.parsed_response is not None

    @pytest.mark.productization
    def test_validation_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """ResponseValidator produced a ValidationResult."""
        assert golden_pipeline_result.validation_result is not None

    @pytest.mark.productization
    def test_cp1_result_exists(self, golden_pipeline_result: PipelineResult) -> None:
        """CP1 Service produced a CP1Result (gate must be open for golden response)."""
        assert golden_pipeline_result.cp1_result is not None, (
            "CP1Result is None — the Validation → CP1 gate was closed. "
            f"Validation verdict: {golden_pipeline_result.validation_result.overall_verdict}"
        )

    @pytest.mark.productization
    def test_execution_package_written(self, golden_pipeline_result: PipelineResult) -> None:
        """ExecutionWriter completed without raising."""
        assert golden_pipeline_result.write_result is not None
        assert golden_pipeline_result.output_dir.is_dir()


# ===========================================================================
# PHASE 4 — Output Verification
# ===========================================================================


class TestPhase4OutputVerification:
    """Every governed artifact must be present, internally consistent, and checksummed."""

    # --- Artifact presence -------------------------------------------------

    @pytest.mark.productization
    def test_all_core_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        for name in _CORE_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Core artifact missing: {name}"
            assert path.stat().st_size > 0, f"Core artifact is empty: {name}"

    @pytest.mark.productization
    def test_all_result_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        for name in _RESULT_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Result artifact missing: {name}"
            assert path.stat().st_size > 0, f"Result artifact is empty: {name}"

    @pytest.mark.productization
    def test_validation_artifacts_present(self, golden_pipeline_result: PipelineResult) -> None:
        for name in _VALIDATION_ARTIFACTS:
            path = golden_pipeline_result.output_dir / name
            assert path.exists(), f"Validation artifact missing: {name}"
            assert path.stat().st_size > 0, f"Validation artifact is empty: {name}"

    @pytest.mark.productization
    def test_cp1_report_present(self, golden_pipeline_result: PipelineResult) -> None:
        path = golden_pipeline_result.output_dir / "cp1_report.md"
        assert path.exists(), "cp1_report.md missing"
        assert path.stat().st_size > 0, "cp1_report.md is empty"

    @pytest.mark.productization
    def test_manifest_present(self, golden_pipeline_result: PipelineResult) -> None:
        path = golden_pipeline_result.output_dir / "manifest.json"
        assert path.exists(), "manifest.json missing"
        assert path.stat().st_size > 0, "manifest.json is empty"

    # --- AnalysisResult verification ---------------------------------------

    @pytest.mark.productization
    def test_analysis_result_json_parseable(self, golden_pipeline_result: PipelineResult) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "analysis_result.json")
        assert "analysisId" in data
        assert "executionId" in data
        assert "provider" in data
        assert "llmResponse" in data

    @pytest.mark.productization
    def test_raw_llm_response_json_parseable(self, golden_pipeline_result: PipelineResult) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "raw_llm_response.json")
        assert "generatedText" in data or "generated_text" in data

    # --- EngineeringContext artifact verification --------------------------

    @pytest.mark.productization
    def test_engineering_context_artifact_records_identity_and_policy(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """engineering_context.json names the context and the rules that composed it."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        context = golden_pipeline_result.engineering_context
        assert data["contextId"] == str(context.context_id)
        assert data["orchestration"]["policyId"] == "coverage"
        assert data["orchestration"]["policyVersion"] == "1.0.0"
        assert data["orchestration"]["selectionStrategy"] == "coverage_guaranteed"
        assert data["orchestrationReason"] == context.orchestration_reason

    @pytest.mark.productization
    def test_engineering_context_artifact_records_evidence_counts(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Evidence counts in the artifact match the nine golden source artifacts."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        counts = data["evidenceCounts"]
        assert counts == {"functional": 4, "security": 3, "quality": 2, "total": 9}
        assert data["provenance"]["sourceArtifactCount"] == 9

    @pytest.mark.productization
    def test_engineering_context_artifact_explains_every_contribution(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every contributing group carries a non-empty, documented inclusion reason."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        contributions = data["provenance"]["contributions"]
        assert contributions, "No contribution was recorded"
        for contribution in contributions:
            assert contribution["consolidatedId"]
            assert contribution["inclusionReason"].strip()
            assert contribution["consolidationReason"].strip()
            assert contribution["rank"] >= 1
            assert contribution["artifactCount"] == contribution["candidateArtifactCount"]

    @pytest.mark.productization
    def test_engineering_context_artifact_summarises_every_evidence_item(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Each evidence artifact is traceable to its origin record."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        summary = data["evidenceSummary"]
        items = summary["functional"] + summary["security"] + summary["quality"]
        assert len(items) == data["evidenceCounts"]["total"]
        for item in items:
            assert item["sourceSystem"] and item["sourceRecordId"] and item["title"]

    # --- NormalizationResult verification ----------------------------------

    @pytest.mark.productization
    def test_parsed_response_has_required_keys(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """ParsedResponse normalized_structure carries all required JSON contract keys."""
        structure = _parsed_response_structure(golden_pipeline_result)
        for key in (
            "summary",
            "functional_requirements",
            "security_requirements",
            "quality_requirements",
            "risks",
            "recommendations",
        ):
            assert key in structure, f"ParsedResponse is missing key: {key}"

    @pytest.mark.productization
    def test_functional_requirements_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["functional_requirements"]) == EXPECTED_FUNCTIONAL_REQUIREMENTS_COUNT

    @pytest.mark.productization
    def test_security_requirements_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["security_requirements"]) == EXPECTED_SECURITY_REQUIREMENTS_COUNT

    @pytest.mark.productization
    def test_quality_requirements_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["quality_requirements"]) == EXPECTED_QUALITY_REQUIREMENTS_COUNT

    @pytest.mark.productization
    def test_risks_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["risks"]) == EXPECTED_RISKS_COUNT

    @pytest.mark.productization
    def test_recommendations_count(self, golden_pipeline_result: PipelineResult) -> None:
        structure = _parsed_response_structure(golden_pipeline_result)
        assert len(structure["recommendations"]) == EXPECTED_RECOMMENDATIONS_COUNT

    # --- ValidationResult verification -------------------------------------

    @pytest.mark.productization
    def test_validation_result_json_parseable(self, golden_pipeline_result: PipelineResult) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "validation_result.json")
        assert "overallVerdict" in data
        assert "validationSummary" in data

    @pytest.mark.productization
    def test_validation_verdict_is_passing(self, golden_pipeline_result: PipelineResult) -> None:
        """Golden response must pass validation (prerequisite for CP1 gate opening)."""
        verdict = golden_pipeline_result.validation_result.overall_verdict
        assert verdict in (ValidationVerdict.PASSED, ValidationVerdict.PASSED_WITH_WARNINGS), (
            f"Expected PASSED or PASSED_WITH_WARNINGS; got {verdict}. "
            "The golden response did not satisfy the validation rules."
        )

    # --- CP1Result verification --------------------------------------------

    @pytest.mark.productization
    def test_cp1_verdict_is_pass(self, golden_pipeline_result: PipelineResult) -> None:
        """CP1-0001 must PASS: the golden response contains ≥1 requirement in all categories."""
        result = golden_pipeline_result.cp1_result
        assert result is not None
        verdict_value = str(getattr(result.overall_verdict, "value", result.overall_verdict))
        assert verdict_value.upper() == "PASS", (
            f"Expected CP1 verdict PASS; got {verdict_value}. "
            "CP1-0001 failed: the golden response must contain at least one requirement."
        )

    @pytest.mark.productization
    def test_cp1_no_fail_findings(self, golden_pipeline_result: PipelineResult) -> None:
        """No CP1 findings with FAIL contribution (golden response is engineering-ready)."""
        result = golden_pipeline_result.cp1_result
        assert result is not None
        fail_findings = [
            f
            for f in result.findings
            if str(getattr(f.verdict_contribution, "value", f.verdict_contribution)).upper()
            == "FAIL"
        ]
        assert len(fail_findings) == 0, (
            f"Found {len(fail_findings)} FAIL finding(s) in the golden CP1 result: "
            + str([f.criterion_id for f in fail_findings])
        )

    # --- Manifest verification ---------------------------------------------

    @pytest.mark.productization
    def test_manifest_schema_version(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest["manifestSchemaVersion"] == "1.0.0"

    @pytest.mark.productization
    def test_manifest_platform_version(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest["platformVersion"] == "1.0.0"

    @pytest.mark.productization
    def test_manifest_execution_mode(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest["executionMode"] == "live"
        assert manifest["dryRun"] is False

    @pytest.mark.productization
    def test_manifest_cp1_executed(self, golden_pipeline_result: PipelineResult) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        assert manifest.get("cp1Executed") is True
        assert manifest.get("cp1Verdict") is not None
        assert manifest.get("cp1Report") == "cp1_report.md"

    @pytest.mark.productization
    def test_manifest_registers_the_engineering_context(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json names the artifact and the policy that produced it."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        context = golden_pipeline_result.engineering_context
        assert manifest["engineeringContextArtifact"] == "engineering_context.json"
        assert manifest["engineeringContextId"] == str(context.context_id)
        assert manifest["orchestrationPolicyId"] == "coverage"
        assert manifest["orchestrationPolicyVersion"] == "1.0.0"
        assert manifest["selectionStrategy"] == "coverage_guaranteed"
        assert manifest["candidateGroupCount"] == 1
        assert manifest["contributingGroupCount"] == 1
        assert manifest["contributingConsolidatedIds"] == list(
            context.provenance.contributing_consolidated_ids
        )
        assert manifest["coverageComplete"] is True
        assert manifest["evidenceDomainsRepresented"] == ["functional", "security", "quality"]
        assert manifest["contextArtifactCount"] == 9

    @pytest.mark.productization
    def test_manifest_checksums_the_engineering_context(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """The new artifact is checksummed by the same mechanism as every other."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        entries = {a["name"]: a for a in manifest["generatedArtifacts"]}
        entry = entries["engineering_context.json"]
        path = golden_pipeline_result.output_dir / "engineering_context.json"
        assert entry["sha256"] == _sha256(path)
        assert entry["bytes"] == path.stat().st_size

    @pytest.mark.productization
    def test_manifest_generated_artifacts_list(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        names = {a["name"] for a in manifest["generatedArtifacts"]}
        # Every governed artifact must appear in the manifest listing.
        for expected in _ALL_ARTIFACTS - {"manifest.json"}:
            assert expected in names, f"Artifact missing from manifest listing: {expected}"

    @pytest.mark.productization
    def test_manifest_checksums_match_files(self, golden_pipeline_result: PipelineResult) -> None:
        """sha256 in manifest.generatedArtifacts must match on-disk content."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        for entry in manifest["generatedArtifacts"]:
            name = entry["name"]
            expected_sha = entry["sha256"]
            actual_sha = _sha256(golden_pipeline_result.output_dir / name)
            assert actual_sha == expected_sha, (
                f"Checksum mismatch for {name}: manifest={expected_sha!r} file={actual_sha!r}"
            )

    @pytest.mark.productization
    def test_manifest_byte_counts_match_files(self, golden_pipeline_result: PipelineResult) -> None:
        """bytes in manifest.generatedArtifacts must match on-disk file size."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        for entry in manifest["generatedArtifacts"]:
            name = entry["name"]
            expected_bytes = entry["bytes"]
            actual_bytes = (golden_pipeline_result.output_dir / name).stat().st_size
            assert actual_bytes == expected_bytes, (
                f"Byte count mismatch for {name}: manifest={expected_bytes} file={actual_bytes}"
            )

    @pytest.mark.productization
    def test_manifest_analysis_id_cross_reference(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.analysisId matches the AnalysisResult written to disk."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        analysis_data = _load_json(golden_pipeline_result.output_dir / "analysis_result.json")
        assert manifest["analysisId"] == analysis_data["analysisId"]

    @pytest.mark.productization
    def test_manifest_execution_id_cross_reference(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.executionId matches the AnalysisResult written to disk."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        analysis_data = _load_json(golden_pipeline_result.output_dir / "analysis_result.json")
        assert manifest["executionId"] == analysis_data["executionId"]

    @pytest.mark.productization
    def test_manifest_prompt_sha256_matches_prompt_txt(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.promptSha256 is the SHA-256 of the full prompt (system + user)."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        full_prompt = golden_pipeline_result.execution_data.full_prompt
        import hashlib

        expected = hashlib.sha256(full_prompt.encode("utf-8")).hexdigest()
        assert manifest["promptSha256"] == expected

    @pytest.mark.productization
    def test_manifest_response_sha256_matches_generated_text(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.responseSha256 is the SHA-256 of the raw LLM response text."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        generated_text = golden_pipeline_result.execution_data.generated_text
        import hashlib

        expected = hashlib.sha256(generated_text.encode("utf-8")).hexdigest()
        assert manifest["responseSha256"] == expected

    # --- Execution summary verification ------------------------------------

    @pytest.mark.productization
    def test_execution_summary_contains_cp1_section(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        content = (golden_pipeline_result.output_dir / "execution_summary.md").read_text()
        assert "Engineering Readiness" in content
        assert "cp1_report.md" in content

    # --- Baseline metrics verification -------------------------------------

    @pytest.mark.productization
    def test_baseline_metrics_source_artifact_count(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        content = (golden_pipeline_result.output_dir / "baseline_metrics.md").read_text()
        assert "9" in content  # Source Artifacts Processed = 9


# ===========================================================================
# PHASE 5 — Determinism
# ===========================================================================


class TestPhase5Determinism:
    """Two consecutive identical pipeline runs must produce the same findings and verdicts."""

    @pytest.mark.productization
    def test_determinism_validation_verdict(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical Validation verdicts."""
        run2 = _run_golden_pipeline(tmp_path)
        v1 = str(golden_pipeline_result.validation_result.overall_verdict)
        v2 = str(run2.validation_result.overall_verdict)
        assert v1 == v2, f"Validation verdict differs: run1={v1!r} run2={v2!r}"

    @pytest.mark.productization
    def test_determinism_validation_issue_count(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same number of validation issues."""
        run2 = _run_golden_pipeline(tmp_path)
        n1 = len(golden_pipeline_result.validation_result.validation_issues)
        n2 = len(run2.validation_result.validation_issues)
        assert n1 == n2, f"Validation issue count differs: run1={n1} run2={n2}"

    @pytest.mark.productization
    def test_determinism_validation_issue_rules(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs report the same rule IDs (order-independent)."""
        run2 = _run_golden_pipeline(tmp_path)
        rules1 = sorted(
            i.rule_id for i in golden_pipeline_result.validation_result.validation_issues
        )
        rules2 = sorted(i.rule_id for i in run2.validation_result.validation_issues)
        assert rules1 == rules2, f"Rule IDs differ: run1={rules1} run2={rules2}"

    @pytest.mark.productization
    def test_determinism_cp1_verdict(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical CP1 verdicts."""
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.cp1_result
        r2 = run2.cp1_result
        assert (r1 is None) == (r2 is None), "CP1 gate open/closed differs between runs"
        if r1 is not None and r2 is not None:
            v1 = str(getattr(r1.overall_verdict, "value", r1.overall_verdict))
            v2 = str(getattr(r2.overall_verdict, "value", r2.overall_verdict))
            assert v1 == v2, f"CP1 verdict differs: run1={v1!r} run2={v2!r}"

    @pytest.mark.productization
    def test_determinism_cp1_finding_count(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same number of CP1 findings."""
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.cp1_result
        r2 = run2.cp1_result
        if r1 is None and r2 is None:
            return  # both skipped — consistent
        assert r1 is not None and r2 is not None
        assert len(r1.findings) == len(r2.findings), (
            f"CP1 finding count differs: run1={len(r1.findings)} run2={len(r2.findings)}"
        )

    @pytest.mark.productization
    def test_determinism_cp1_criterion_ids(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs report the same CP1 criterion IDs (order-independent)."""
        run2 = _run_golden_pipeline(tmp_path)
        r1 = golden_pipeline_result.cp1_result
        r2 = run2.cp1_result
        if r1 is None and r2 is None:
            return
        assert r1 is not None and r2 is not None
        cids1 = sorted(f.criterion_id for f in r1.findings)
        cids2 = sorted(f.criterion_id for f in r2.findings)
        assert cids1 == cids2, f"CP1 criterion IDs differ: run1={cids1} run2={cids2}"

    @pytest.mark.productization
    def test_determinism_normalization_outcome(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical normalization outcomes."""
        run2 = _run_golden_pipeline(tmp_path)
        pr1 = golden_pipeline_result.normalization_result.parsed_response
        pr2 = run2.normalization_result.parsed_response
        assert (pr1 is None) == (pr2 is None), "ParsedResponse presence differs"
        if pr1 is not None and pr2 is not None:
            outcome1 = str(getattr(pr1.normalization_outcome, "value", pr1.normalization_outcome))
            outcome2 = str(getattr(pr2.normalization_outcome, "value", pr2.normalization_outcome))
            assert outcome1 == outcome2, (
                f"Normalization outcome differs: run1={outcome1!r} run2={outcome2!r}"
            )

    @pytest.mark.productization
    def test_determinism_parsed_response_structure(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce identical ParsedResponse normalized structures."""
        run2 = _run_golden_pipeline(tmp_path)
        s1 = _parsed_response_structure(golden_pipeline_result)
        s2 = _parsed_response_structure(run2)
        assert s1 == s2, "ParsedResponse.normalized_structure differs between runs"

    @pytest.mark.productization
    def test_determinism_consolidated_artifact_count(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs produce the same number of consolidated artifacts."""
        run2 = _run_golden_pipeline(tmp_path)
        n1 = len(golden_pipeline_result.consolidated_artifacts)
        n2 = len(run2.consolidated_artifacts)
        assert n1 == n2, f"Consolidated artifact count differs: run1={n1} run2={n2}"

    @pytest.mark.productization
    def test_determinism_consolidated_module_name(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """Two runs select the identical consolidated module."""
        run2 = _run_golden_pipeline(tmp_path)
        assert golden_pipeline_result.selected.module == run2.selected.module

    @pytest.mark.productization
    def test_determinism_manifest_cp1_verdict_field(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """manifest.cp1Verdict is identical across two runs."""
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1.get("cp1Verdict") == m2.get("cp1Verdict"), (
            f"manifest.cp1Verdict differs: run1={m1.get('cp1Verdict')!r} "
            f"run2={m2.get('cp1Verdict')!r}"
        )

    @pytest.mark.productization
    def test_determinism_response_sha256(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """The raw LLM response text (and its SHA-256) is identical across runs."""
        run2 = _run_golden_pipeline(tmp_path)
        text1 = golden_pipeline_result.execution_data.generated_text
        text2 = run2.execution_data.generated_text
        assert text1 == text2, "Generated text differs between runs"

    @pytest.mark.productization
    def test_determinism_engineering_context_id(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """The context identity is a pure function of its inputs — never a uuid or clock."""
        run2 = _run_golden_pipeline(tmp_path)
        id1 = str(golden_pipeline_result.engineering_context.context_id)
        id2 = str(run2.engineering_context.context_id)
        assert id1 == id2, f"Context id differs: run1={id1!r} run2={id2!r}"

    @pytest.mark.productization
    def test_determinism_engineering_context_artifact_bytes(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """engineering_context.json is byte-identical across two runs."""
        run2 = _run_golden_pipeline(tmp_path)
        sha1 = _sha256(golden_pipeline_result.output_dir / "engineering_context.json")
        sha2 = _sha256(run2.output_dir / "engineering_context.json")
        assert sha1 == sha2, "engineering_context.json differs between runs"

    @pytest.mark.productization
    def test_determinism_prompt_sha256(
        self,
        golden_pipeline_result: PipelineResult,
        tmp_path: Path,
    ) -> None:
        """The orchestrated prompt is byte-identical across two runs."""
        run2 = _run_golden_pipeline(tmp_path)
        m1 = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        m2 = _load_json(run2.output_dir / "manifest.json")
        assert m1["promptSha256"] == m2["promptSha256"]


# ===========================================================================
# PHASE 6 — Productization Assertions
# ===========================================================================


class TestPhase6ProductizationAssertions:
    """Structured per-layer contract checks that serve as long-term regression guards."""

    # --- Dataset integrity -------------------------------------------------

    @pytest.mark.productization
    def test_dataset_version(self) -> None:
        """The golden dataset declares a version."""
        assert GOLDEN_DATASET_VERSION == "1.0.0"

    @pytest.mark.productization
    def test_dataset_covers_all_categories(self) -> None:
        """Dataset includes at least one artifact in each governed category."""
        categories = {a.source_category for a in GOLDEN_SOURCE_ARTIFACTS}
        assert SourceCategory.FUNCTIONAL in categories
        assert SourceCategory.SECURITY in categories
        assert SourceCategory.QUALITY in categories

    @pytest.mark.productization
    def test_dataset_artifact_ids_unique(self) -> None:
        """All artifact IDs in the golden dataset are unique."""
        ids = [a.artifact_id for a in GOLDEN_SOURCE_ARTIFACTS]
        assert len(ids) == len(set(ids)), "Duplicate artifact IDs in golden dataset"

    # --- Pipeline contract -------------------------------------------------

    @pytest.mark.productization
    def test_analysis_result_prompt_version(self, golden_pipeline_result: PipelineResult) -> None:
        """AnalysisResult carries the governed prompt version."""
        assert golden_pipeline_result.analysis_result.prompt_version == "1.0.0"

    @pytest.mark.productization
    def test_analysis_result_reasoning_contract_version(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """AnalysisResult carries the governed reasoning contract version."""
        assert golden_pipeline_result.analysis_result.reasoning_contract_version == "1.0.0"

    @pytest.mark.productization
    def test_normalization_statistics_populated(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """NormalizationResult statistics are populated."""
        stats = golden_pipeline_result.normalization_result.normalization_statistics
        assert stats is not None
        assert stats.responsibilities_executed >= 0

    @pytest.mark.productization
    def test_validation_statistics_rules_executed(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """ValidationResult statistics show at least one rule was executed."""
        stats = golden_pipeline_result.validation_result.validation_statistics
        assert stats.rules_executed > 0, "No validation rules were executed"

    @pytest.mark.productization
    def test_cp1_framework_metadata_present(self, golden_pipeline_result: PipelineResult) -> None:
        """CP1Result carries framework metadata."""
        result = golden_pipeline_result.cp1_result
        assert result is not None
        assert result.framework_metadata is not None

    @pytest.mark.productization
    def test_cp1_input_cross_references_validation(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """CP1Input.validation_id matches the ValidationResult.validation_id."""
        cp1_result = golden_pipeline_result.cp1_result
        validation_result = golden_pipeline_result.validation_result
        assert cp1_result is not None
        assert cp1_result.validation_id == validation_result.validation_id

    @pytest.mark.productization
    def test_execution_data_no_dry_run(self, golden_pipeline_result: PipelineResult) -> None:
        """Execution data records a live (non-dry-run) execution."""
        assert golden_pipeline_result.execution_data.dry_run is False

    @pytest.mark.productization
    def test_write_result_json_valid(self, golden_pipeline_result: PipelineResult) -> None:
        """ExecutionWriter confirms the LLM response is valid JSON."""
        assert golden_pipeline_result.write_result.json_valid is True

    @pytest.mark.productization
    def test_manifest_all_version_fields_present(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """manifest.json contains every governed version field."""
        manifest = _load_json(golden_pipeline_result.output_dir / "manifest.json")
        for key in (
            "manifestSchemaVersion",
            "platformVersion",
            "baselineVersion",
            "executionPackageVersion",
            "connectorRegistryVersion",
            "mapperVersion",
            "consolidationEngineVersion",
            "promptFrameworkVersion",
            "llmFrameworkVersion",
            "analysisServiceVersion",
            "executionWriterVersion",
            "platformCapabilitiesVersion",
        ):
            assert key in manifest, f"Version field missing from manifest: {key}"
            assert manifest[key], f"Version field is empty in manifest: {key}"

    @pytest.mark.productization
    def test_validation_report_contains_verdict(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """validation_report.md renders the overall verdict."""
        content = (golden_pipeline_result.output_dir / "validation_report.md").read_text()
        assert "PASSED" in content.upper()

    @pytest.mark.productization
    def test_cp1_report_contains_verdict(self, golden_pipeline_result: PipelineResult) -> None:
        """cp1_report.md renders the CP1 overall verdict."""
        content = (golden_pipeline_result.output_dir / "cp1_report.md").read_text()
        assert "PASS" in content.upper()

    # --- Explainability (CAP-076C Stage 9) ---------------------------------

    @pytest.mark.productization
    def test_context_carries_an_orchestration_reason(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every EngineeringContext explains, in one sentence, why it was composed."""
        reason = golden_pipeline_result.engineering_context.orchestration_reason
        assert reason.strip()
        assert golden_pipeline_result.engineering_context.subject.label in reason

    @pytest.mark.productization
    def test_every_contributing_group_has_an_inclusion_reason(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """No group is present without a recorded reason naming the policy that admitted it."""
        provenance = golden_pipeline_result.engineering_context.provenance
        policy_id = str(golden_pipeline_result.engineering_context.orchestration.policy_id)
        for contribution in provenance.contributions:
            assert contribution.inclusion_reason.strip()
            assert policy_id in contribution.inclusion_reason

    @pytest.mark.productization
    def test_provenance_records_every_candidate_the_policy_ranked(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Selection is falsifiable: the context records what it was chosen *from*."""
        provenance = golden_pipeline_result.engineering_context.provenance
        assert provenance.candidate_group_count == len(
            golden_pipeline_result.consolidated_artifacts
        )

    @pytest.mark.productization
    def test_every_evidence_artifact_is_traceable_to_its_source_record(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """No evidence item is anonymous: each carries its origin system and record id."""
        evidence = golden_pipeline_result.engineering_context.evidence
        artifacts = (
            *evidence.functional_artifacts,
            *evidence.security_artifacts,
            *evidence.quality_artifacts,
        )
        assert len(artifacts) == evidence.total_count
        for artifact in artifacts:
            assert artifact.source_system and artifact.source_record_id


# ===========================================================================
# CAP-076D — EngineeringContext as a first-class governed execution artifact
# ===========================================================================


class TestEngineeringContextGovernance:
    """The Golden Baseline verifies the *context*, not a single selected group.

    Before CAP-076D the baseline pinned the ConsolidatedArtifact the runtime
    selected. That was the right subject when a context was a single group. It no
    longer is: the context is the complete reasoning input, and the group is one
    of its contributors. These tests govern the context and every orchestration
    decision recorded inside it.
    """

    @pytest.mark.productization
    def test_context_artifact_records_the_full_ranking(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Every candidate group appears, with the score it was ranked on."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        context = golden_pipeline_result.engineering_context
        ranking = data["ranking"]
        assert ranking["keys"] == list(context.ranking.keys)
        assert ranking["tieBreaker"] == context.ranking.tie_breaker
        assert len(ranking["entries"]) == context.provenance.candidate_group_count
        for entry in ranking["entries"]:
            assert entry["decisionReason"].strip()
            assert len(entry["score"]) == len(ranking["keys"])

    @pytest.mark.productization
    def test_context_artifact_partitions_selected_and_excluded_groups(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Both halves of the ranking are named; an exclusion is never implicit."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        selected = data["selectedGroups"]
        excluded = data["excludedGroups"]
        assert len(selected) + len(excluded) == data["candidateGroupCount"]
        assert len(selected) == data["contributingGroupCount"]
        for group in selected:
            assert group["inclusionReason"].strip()
        for group in excluded:
            assert group["exclusionReason"].strip()

    @pytest.mark.productization
    def test_context_artifact_records_coverage_per_domain(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        coverage = data["coverage"]
        assert coverage["mode"] == "all_present_categories"
        assert coverage["ruleSatisfied"] is True
        assert coverage["allPresentCategoriesRepresented"] is True
        assert [d["category"] for d in coverage["domains"]] == [
            "functional",
            "security",
            "quality",
        ]
        for domain in coverage["domains"]:
            assert domain["reason"].strip()

    @pytest.mark.productization
    def test_context_artifact_records_the_evidence_budget(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        budget = data["evidenceBudget"]
        assert budget["maxArtifactsPerDomain"] == 25
        assert budget["maxArtifactsTotal"] == 60
        assert budget["totalUsed"] == 9
        assert budget["truncated"] is False
        assert sum(d["used"] for d in budget["domains"]) == budget["totalUsed"]

    @pytest.mark.productization
    def test_context_artifact_records_grounding_metadata(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        """Grounding names the domains, the counts and the systems the evidence came from."""
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        grounding = data["groundingMetadata"]
        assert grounding["evidenceDomains"] == ["functional", "security", "quality"]
        assert grounding["evidenceCounts"] == {
            "functional": 4,
            "security": 3,
            "quality": 2,
            "total": 9,
        }
        assert grounding["coverageAchieved"] is True
        systems = {e["sourceSystem"]: e["artifactCount"] for e in grounding["sourceDistribution"]}
        assert systems == {"jira": 4, "owasp_zap": 3, "sonarqube": 2}
        assert sum(systems.values()) == grounding["evidenceCounts"]["total"]

    @pytest.mark.productization
    def test_context_artifact_declares_its_contract_version(
        self, golden_pipeline_result: PipelineResult
    ) -> None:
        data = _load_json(golden_pipeline_result.output_dir / "engineering_context.json")
        assert data["engineeringContextArtifactVersion"] == "2.0.0"
        assert data["contextModelVersion"] == "1.2"


class TestPolicyComparison:
    """Legacy versus Default over the identical candidate set (CAP-076D Stage 9).

    The golden dataset consolidates to one group carrying all three domains, so it
    isolates exactly one difference between the policies: the order evidence is
    presented in. Every other output must be identical, and that is the point —
    a difference anywhere else would mean the policy flip changed something the
    policy does not govern.
    """

    @pytest.mark.productization
    def test_both_policies_select_the_same_group(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        assert (
            golden_pipeline_result.selected.consolidated_id
            == legacy_pipeline_result.selected.consolidated_id
        )

    @pytest.mark.productization
    def test_both_policies_deliver_the_same_evidence_for_this_dataset(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        """One group, whole, under both policies — only the ordering differs."""
        active = golden_pipeline_result.engineering_context.evidence
        legacy = legacy_pipeline_result.engineering_context.evidence
        assert active.total_count == legacy.total_count == 9
        assert sorted(a.source_record_id for a in active.security_artifacts) == sorted(
            a.source_record_id for a in legacy.security_artifacts
        )

    @pytest.mark.productization
    def test_the_policies_disagree_only_where_the_policy_says_they_should(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        """Same context identity and subject; different recorded policy and ordering."""
        active = golden_pipeline_result.engineering_context
        legacy = legacy_pipeline_result.engineering_context
        assert active.context_id == legacy.context_id  # same subject, same groups
        assert str(active.orchestration.policy_id) == "coverage"
        assert str(legacy.orchestration.policy_id) == "legacy-single-largest"
        assert active.coverage.selection_strategy == "coverage_guaranteed"
        assert legacy.coverage.selection_strategy == "single_largest"

    @pytest.mark.productization
    def test_both_policies_produce_identical_validation_and_cp1_outcomes(
        self,
        golden_pipeline_result: PipelineResult,
        legacy_pipeline_result: PipelineResult,
    ) -> None:
        """Validation and CP1 are unchanged by CAP-076D and must not react to the policy."""
        assert (
            golden_pipeline_result.validation_result.overall_verdict
            == legacy_pipeline_result.validation_result.overall_verdict
        )
        assert golden_pipeline_result.cp1_result is not None
        assert legacy_pipeline_result.cp1_result is not None
        assert (
            golden_pipeline_result.cp1_result.overall_verdict
            == legacy_pipeline_result.cp1_result.overall_verdict
        )

    @pytest.mark.productization
    def test_the_legacy_policy_still_reproduces_the_pre_cap_076_selection(
        self, legacy_pipeline_result: PipelineResult
    ) -> None:
        """The control arm is only a control if it still controls."""
        context = legacy_pipeline_result.engineering_context
        assert context.provenance.contributing_group_count == 1
        assert context.coverage.rule_satisfied is True
        evidence = context.evidence
        selected = legacy_pipeline_result.selected
        assert list(evidence.functional_artifacts) == selected.functional_artifacts
        assert list(evidence.security_artifacts) == selected.security_artifacts
        assert list(evidence.quality_artifacts) == selected.quality_artifacts
