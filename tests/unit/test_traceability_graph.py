"""Traceability Graph — the minimal `requirement -> scenario -> step` slice
and its completeness report (mentor item #3, both mentors' #1 strategic
risk).

Proves, deterministically, with fixture requirements/features (no LLM, no
live run): the projector builds the expected graph from real
`TestableRequirementSet` + `FeatureEngineeringPackage` + on-disk `.feature`
files; the completeness sweep correctly separates tested from untested
requirements with the right reason per gap; the graph's own
cross-referential invariant rejects a dangling edge; the report's own
consistency invariant rejects mismatched counts; the module reuses only the
ADR-0023 *pattern* (never its code) — a containment test proves no import
of `requirement_intelligence.knowledge_graph` anywhere in this package.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from automation_engineering.stage.models import AssetRecord, AutomationEngineeringPackage
from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    Priority,
    RequirementQualityGovernanceDecision,
    TestableRequirement,
    TestableRequirementSet,
    TestableRequirementSetProvenance,
    build_testable_requirement,
)
from feature_engineering.stage.models import FeatureEngineeringPackage, FeatureRecord
from requirement_intelligence.traceability_graph import (
    BindingCompletenessReport,
    ChangeImpactReport,
    CompletenessReport,
    MethodImpact,
    TraceabilityEdge,
    TraceabilityEdgeType,
    TraceabilityGraph,
    TraceabilityNode,
    TraceabilityNodeType,
    UnboundStep,
    UncoveredRequirement,
    build_change_impact_report,
    build_directed_adjacency,
    build_reverse_directed_adjacency,
    change_impact_for_method,
    edge_id_for,
    evaluate_binding_completeness,
    evaluate_completeness,
    graph_id_for,
    node_id_for,
    project_change_impact,
    project_traceability_graph,
    reachable_from,
    render_binding_completeness_json,
    render_binding_completeness_report,
    render_change_impact_json,
    render_change_impact_report,
    render_completeness_json,
    render_completeness_report,
    render_graph_json,
    render_graph_report,
)

_TESTED_FEATURE = """Feature: Password reset

  @SCN-TESTED-001
  Scenario: Reset succeeds
    Given a precondition
    When an action occurs
    Then an outcome is observed
"""

_NO_SCENARIO_TAG_FEATURE = """Feature: Untagged

  Scenario: Not traceable
    Given a precondition
    Then an outcome is observed
"""

_EMPTY_SCENARIO_FEATURE = """Feature: Empty scenario

  @SCN-EMPTY-001
  Scenario: No steps at all
"""

_IMPACT_FEATURE = """Feature: Change impact test

  @SCN-S1
  Scenario: First login
    Given user logs in

  @SCN-S2
  Scenario: Second login
    Given user logs in

  @SCN-S3
  Scenario: Logout
    Given user logs out
"""

_LOGIN_STEP_JAVA = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class LoginSteps {
    private LoginPage loginPage;

    @Given("user logs in")
    public void userLogsIn() {
        loginPage.clickLogin();
    }
}
"""

_LOGOUT_STEP_JAVA = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class LogoutSteps {
    private DashboardPage dashboardPage;

    @Given("user logs out")
    public void userLogsOut() {
        dashboardPage.logout();
    }
}
"""


def _requirement(requirement_id_seed: str, **overrides: object) -> TestableRequirement:
    defaults: dict[str, object] = {
        "title": f"Requirement {requirement_id_seed}",
        "component": "auth",
        "functional_tag": "@auth",
        "priority": Priority.HIGH,
        "traces_to": (),
        "narrative": f"Narrative for {requirement_id_seed}.",
        "acceptance_criteria": [
            AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement=requirement_id_seed),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


def _requirement_set(
    requirements: list[TestableRequirement], *, run_id: str = "run-traceability-test"
) -> TestableRequirementSet:
    return TestableRequirementSet(
        run_id=run_id,
        generated_at=datetime.now(UTC),
        provenance=TestableRequirementSetProvenance(
            prompt_id="requirement_analysis",
            prompt_version="1.0.0",
            prompt_sha256="0" * 64,
            provider="stub",
            model="stub-model",
            requirement_quality_governance_decision=RequirementQualityGovernanceDecision.PASS,
            governance_report_ref="quality_governance_report.md",
        ),
        requirements=tuple(requirements),
        risks=(),
    )


def _feature_record(
    requirement_id: str, feature_path: str | None, *, escalated: bool = False
) -> FeatureRecord:
    return FeatureRecord(
        requirement_id=requirement_id,
        content_hash=f"hash-{requirement_id}",
        req_tag=f"@{requirement_id}",
        feature_path=feature_path,
        scn_ids=(),
        ac_ids_covered=(),
        cp2_verdict="fail" if escalated else "pass",
        remediated=False,
        escalated=escalated,
        escalation_reason="upstream CP2 escalation" if escalated else None,
    )


def _package(records: tuple[FeatureRecord, ...], *, run_id: str = "run-traceability-test") -> (
    FeatureEngineeringPackage
):
    return FeatureEngineeringPackage(
        contract_version="1.0.0",
        run_id=run_id,
        requirement_set_run_id=run_id,
        generated_at=datetime.now(UTC).isoformat(),
        records=records,
    )


def _asset_record(
    need_text: str, *, need_kind: str = "step_definition", escalated: bool = False
) -> AssetRecord:
    return AssetRecord(
        need_text=need_text,
        need_kind=need_kind,
        outcome="escalated" if escalated else "bound",
        class_name=None if escalated else "com.automation.steps.Steps",
        target_package=None,
        workspace_path=None,
        escalated=escalated,
        escalation_check="confidence" if escalated else None,
        escalation_reason="match confidence below threshold" if escalated else None,
        promotion_status=None,
        promotion_detail=None,
        promoted_path=None,
    )


def _automation_package(
    records: tuple[AssetRecord, ...], *, run_id: str = "run-traceability-test"
) -> AutomationEngineeringPackage:
    return AutomationEngineeringPackage(
        contract_version="1.0.0",
        run_id=run_id,
        feature_engineering_run_id=run_id,
        generated_at=datetime.now(UTC).isoformat(),
        records=records,
    )


def _generated_asset_record(need_text: str, class_name: str, workspace_path: str) -> AssetRecord:
    """A `"generated"` step-definition record — real `workspace_path`, the
    only outcome `project_change_impact` reads a Java source for (module
    docstring's own scope: `"bound"`/`"escalated"` records are excluded)."""
    return AssetRecord(
        need_text=need_text,
        need_kind="step_definition",
        outcome="generated",
        class_name=class_name,
        target_package="com.automation.steps",
        workspace_path=workspace_path,
        escalated=False,
        escalation_check=None,
        escalation_reason=None,
        promotion_status=None,
        promotion_detail=None,
        promoted_path=None,
    )


_ImpactFixture = tuple[TraceabilityGraph, AutomationEngineeringPackage, Path]


@pytest.fixture
def change_impact_fixture(tmp_path: Path) -> _ImpactFixture:
    """Two scenarios (S1, S2) share the literal step text "user logs in"
    (dedup-by-text, mirroring `derive_unique_step_needs`'s own rule) and are
    bound to a GENERATED `LoginSteps` class whose body calls
    `LoginPage.clickLogin()`; a third (S3) uses distinct text "user logs
    out", bound to a GENERATED `LogoutSteps` class calling
    `DashboardPage.logout()` — proving the affected set correctly narrows to
    exactly the scenarios that route through a given method."""
    req = _requirement("A")
    requirement_set = _requirement_set([req])
    features_root = tmp_path / "features"
    features_root.mkdir()
    (features_root / "impact.feature").write_text(_IMPACT_FEATURE, encoding="utf-8")
    package = _package((_feature_record(req.requirement_id, "impact.feature"),))
    graph = project_traceability_graph(requirement_set, package, features_root=features_root)

    workspace_dir = tmp_path / "workspace"
    steps_dir = workspace_dir / "steps"
    steps_dir.mkdir(parents=True)
    (steps_dir / "LoginSteps.java").write_text(_LOGIN_STEP_JAVA, encoding="utf-8")
    (steps_dir / "LogoutSteps.java").write_text(_LOGOUT_STEP_JAVA, encoding="utf-8")

    automation_package = _automation_package(
        (
            _generated_asset_record("user logs in", "LoginSteps", "steps/LoginSteps.java"),
            _generated_asset_record("user logs out", "LogoutSteps", "steps/LogoutSteps.java"),
        )
    )
    return graph, automation_package, workspace_dir


_Fixture = tuple[TestableRequirementSet, FeatureEngineeringPackage, Path]


@pytest.fixture
def four_requirement_fixture(tmp_path: Path) -> _Fixture:
    """Requirement A: real scenario+steps (tested). B: escalated, no feature
    content at all (untested/no_scenario). C: no `FeatureRecord` whatsoever
    (untested/no_scenario). D: real scenario, zero steps
    (untested/scenario_without_steps)."""
    req_a = _requirement("A", title="Tested requirement")
    req_b = _requirement("B", title="Escalated requirement")
    req_c = _requirement("C", title="Never-recorded requirement")
    req_d = _requirement("D", title="Empty-scenario requirement")

    requirement_set = _requirement_set([req_a, req_b, req_c, req_d])

    features_root = tmp_path / "features"
    features_root.mkdir()
    (features_root / "tested.feature").write_text(_TESTED_FEATURE, encoding="utf-8")
    (features_root / "empty_scenario.feature").write_text(_EMPTY_SCENARIO_FEATURE, encoding="utf-8")

    records = (
        _feature_record(req_a.requirement_id, "tested.feature"),
        _feature_record(req_b.requirement_id, None, escalated=True),
        # req_c: deliberately no FeatureRecord at all.
        _feature_record(req_d.requirement_id, "empty_scenario.feature"),
    )
    package = _package(records)
    return requirement_set, package, features_root


class TestProjection:
    def test_builds_expected_nodes_and_edges(self, tmp_path: Path) -> None:
        req = _requirement("A")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "tested.feature").write_text(_TESTED_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "tested.feature"),))

        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        node_types = {node.node_type for node in graph.nodes}
        assert node_types == {
            TraceabilityNodeType.REQUIREMENT,
            TraceabilityNodeType.SCENARIO,
            TraceabilityNodeType.STEP,
        }
        assert len(graph.nodes) == 1 + 1 + 3  # requirement + scenario + 3 steps
        edge_types = {edge.edge_type for edge in graph.edges}
        assert edge_types == {TraceabilityEdgeType.HAS_SCENARIO, TraceabilityEdgeType.HAS_STEP}
        assert len(graph.edges) == 1 + 3  # has_scenario + 3x has_step

        requirement_node = next(
            n for n in graph.nodes if n.node_type == TraceabilityNodeType.REQUIREMENT
        )
        assert requirement_node.referenced_id == req.requirement_id
        scenario_node = next(n for n in graph.nodes if n.node_type == TraceabilityNodeType.SCENARIO)
        assert scenario_node.referenced_id == "SCN-TESTED-001"

    def test_requirement_with_no_record_still_gets_a_node(self, tmp_path: Path) -> None:
        req = _requirement("C")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        package = _package(())  # no records at all

        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        assert len(graph.nodes) == 1
        assert graph.nodes[0].node_type == TraceabilityNodeType.REQUIREMENT
        assert graph.edges == ()

    def test_untagged_scenario_is_excluded_like_traceability_json(self, tmp_path: Path) -> None:
        req = _requirement("E")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "untagged.feature").write_text(_NO_SCENARIO_TAG_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "untagged.feature"),))

        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        # Only the requirement node -- the untagged scenario contributes nothing,
        # mirroring build_traceability_index's own behaviour.
        assert len(graph.nodes) == 1
        assert graph.nodes[0].node_type == TraceabilityNodeType.REQUIREMENT

    def test_is_deterministic(
        self, four_requirement_fixture: _Fixture
    ) -> None:
        requirement_set, package, features_root = four_requirement_fixture

        graph_1 = project_traceability_graph(requirement_set, package, features_root=features_root)
        graph_2 = project_traceability_graph(requirement_set, package, features_root=features_root)

        assert graph_1 == graph_2
        assert graph_1.graph_id == graph_2.graph_id


class TestCompletenessDetection:
    def test_detects_gaps_with_correct_reasons(
        self, four_requirement_fixture: _Fixture
    ) -> None:
        requirement_set, package, features_root = four_requirement_fixture
        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        report = evaluate_completeness(graph)

        assert report.total_requirements == 4
        assert report.tested_requirement_count == 1
        assert report.untested_requirement_count == 3
        assert report.coverage_percentage == 25.0

        reasons_by_requirement = {u.requirement_id: u.reason for u in report.untested_requirements}
        (req_a, req_b, req_c, req_d) = requirement_set.requirements
        assert req_a.requirement_id not in reasons_by_requirement  # tested
        assert reasons_by_requirement[req_b.requirement_id] == "no_scenario"  # escalated
        assert reasons_by_requirement[req_c.requirement_id] == "no_scenario"  # no record
        assert reasons_by_requirement[req_d.requirement_id] == "scenario_without_steps"

    def test_full_coverage_yields_100_percent(self, tmp_path: Path) -> None:
        req = _requirement("A")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "tested.feature").write_text(_TESTED_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "tested.feature"),))
        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        report = evaluate_completeness(graph)

        assert report.coverage_percentage == 100.0
        assert report.untested_requirements == ()

    def test_zero_requirements_is_handled_without_division_error(self) -> None:
        empty_graph = TraceabilityGraph(graph_id=graph_id_for("run-empty"), nodes=(), edges=())

        report = evaluate_completeness(empty_graph)

        assert report.total_requirements == 0
        assert report.coverage_percentage == 0.0
        assert report.untested_requirements == ()

    def test_report_structure_is_gate_ready_but_has_no_gating(self) -> None:
        """The report exposes counts/coverage a future gate could read -- but
        nothing in this build evaluates them against any bound."""
        report = CompletenessReport(
            graph_id="tg-000000000000",
            total_requirements=2,
            tested_requirement_count=1,
            untested_requirement_count=1,
            coverage_percentage=50.0,
            untested_requirements=(
                UncoveredRequirement(requirement_id="REQ-1", reason="no_scenario"),
            ),
        )
        # Gate-ready: every field a threshold/pass-fail decision would need.
        assert report.coverage_percentage == 50.0
        assert report.untested_requirement_count == 1
        # No gating vocabulary exists on the model or anywhere in this package.
        assert not hasattr(report, "passed")
        assert not hasattr(report, "verdict")
        assert not hasattr(report, "gate_status")

        import requirement_intelligence.traceability_graph as package

        assert not any(
            name in package.__all__
            for name in ("evaluate_gate", "check_threshold", "GateDecision", "GateResult")
        )


class TestBindingCompleteness:
    """The step-definition-binding hop (ADR-0048 D4/D5): a companion
    completeness layer over the SAME `requirement -> scenario -> step`
    graph, joined against the automation-engineering stage's own per-need
    binding outcomes."""

    def _tested_graph(self, tmp_path: Path) -> TraceabilityGraph:
        req = _requirement("A")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "tested.feature").write_text(_TESTED_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "tested.feature"),))
        return project_traceability_graph(requirement_set, package, features_root=features_root)

    def test_bound_escalated_and_missing_needs_are_distinguished(self, tmp_path: Path) -> None:
        """`_TESTED_FEATURE` has 3 steps: 'a precondition', 'an action occurs',
        'an outcome is observed'. One is bound, one is escalated, and one has
        no automation-package record at all -- the three distinct outcomes
        the join must separate."""
        graph = self._tested_graph(tmp_path)
        automation_package = _automation_package(
            (
                _asset_record("a precondition", escalated=False),
                _asset_record("an action occurs", escalated=True),
                # "an outcome is observed" deliberately absent.
            )
        )

        report = evaluate_binding_completeness(graph, automation_package)

        assert report.total_steps == 3
        assert report.bound_step_count == 1
        assert report.unbound_step_count == 2
        assert report.coverage_percentage == pytest.approx(33.33, abs=0.01)

        reasons_by_text = {u.step_text: u.reason for u in report.unbound_steps}
        assert reasons_by_text["an action occurs"] == "escalated"
        assert reasons_by_text["an outcome is observed"] == "no_step_definition_need"
        assert "a precondition" not in reasons_by_text

    def test_full_binding_coverage_yields_100_percent(self, tmp_path: Path) -> None:
        graph = self._tested_graph(tmp_path)
        automation_package = _automation_package(
            tuple(
                _asset_record(text, escalated=False)
                for text in ("a precondition", "an action occurs", "an outcome is observed")
            )
        )

        report = evaluate_binding_completeness(graph, automation_package)

        assert report.coverage_percentage == 100.0
        assert report.unbound_steps == ()

    def test_non_step_definition_records_never_count_as_a_binding(self, tmp_path: Path) -> None:
        """A `test_data` need sharing a step's own text must never be read as
        that step's step-definition binding -- only `need_kind ==
        "step_definition"` records are eligible."""
        graph = self._tested_graph(tmp_path)
        automation_package = _automation_package(
            (_asset_record("a precondition", need_kind="test_data", escalated=False),)
        )

        report = evaluate_binding_completeness(graph, automation_package)

        assert report.bound_step_count == 0
        assert report.unbound_step_count == 3
        assert {u.reason for u in report.unbound_steps} == {"no_step_definition_need"}

    def test_zero_steps_is_handled_without_division_error(self) -> None:
        empty_graph = TraceabilityGraph(graph_id=graph_id_for("run-empty"), nodes=(), edges=())

        report = evaluate_binding_completeness(empty_graph, _automation_package(()))

        assert report.total_steps == 0
        assert report.coverage_percentage == 0.0
        assert report.unbound_steps == ()

    def test_authoring_and_binding_are_two_distinct_layers_on_one_graph(
        self, tmp_path: Path
    ) -> None:
        """A step fully reachable (authoring-complete) may still be unbound
        (binding-incomplete) -- the exact two-layer picture ADR-0048 D5's
        real measurement first surfaced via a manual CP3 cross-reference."""
        graph = self._tested_graph(tmp_path)
        automation_package = _automation_package(
            (
                _asset_record("a precondition", escalated=False),
                _asset_record("an action occurs", escalated=True),
                _asset_record("an outcome is observed", escalated=True),
            )
        )

        authoring = evaluate_completeness(graph)
        binding = evaluate_binding_completeness(graph, automation_package)

        assert authoring.coverage_percentage == 100.0
        assert authoring.untested_requirements == ()
        assert binding.coverage_percentage == pytest.approx(33.33, abs=0.01)
        assert binding.unbound_step_count == 2

    def test_report_structure_is_gate_ready_but_has_no_gating(self) -> None:
        report = BindingCompletenessReport(
            graph_id="tg-000000000000",
            total_steps=2,
            bound_step_count=1,
            unbound_step_count=1,
            coverage_percentage=50.0,
            unbound_steps=(UnboundStep(step_id="step-1", step_text="a step", reason="escalated"),),
        )
        assert report.coverage_percentage == 50.0
        assert not hasattr(report, "passed")
        assert not hasattr(report, "verdict")
        assert not hasattr(report, "gate_status")

        import requirement_intelligence.traceability_graph as package

        assert not any(
            name in package.__all__
            for name in ("evaluate_gate", "check_threshold", "GateDecision", "GateResult")
        )


class TestChangeImpactProjection:
    """Method-level change-impact (ADR-0048 D4's own "change-impact graph"):
    extends the SAME `TraceabilityGraph` with `PAGE_OBJECT_METHOD` nodes and
    `CALLS_METHOD` edges, sourced from the platform's own already-built
    `derive_page_object_requests` call-site derivation."""

    def test_extends_the_same_graph_with_method_nodes_and_edges(
        self, change_impact_fixture: _ImpactFixture
    ) -> None:
        graph, automation_package, workspace_dir = change_impact_fixture

        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        # The base requirement/scenario/step nodes+edges are preserved, not replaced.
        assert extended.graph_id == graph.graph_id
        base_node_ids = {node.node_id for node in graph.nodes}
        base_edge_ids = {edge.edge_id for edge in graph.edges}
        extended_node_ids = {node.node_id for node in extended.nodes}
        extended_edge_ids = {edge.edge_id for edge in extended.edges}
        assert base_node_ids <= extended_node_ids
        assert base_edge_ids <= extended_edge_ids

        method_nodes = {
            (n.node_type, n.referenced_id)
            for n in extended.nodes
            if n.node_type == TraceabilityNodeType.PAGE_OBJECT_METHOD
        }
        assert method_nodes == {
            (TraceabilityNodeType.PAGE_OBJECT_METHOD, "LoginPage.clickLogin"),
            (TraceabilityNodeType.PAGE_OBJECT_METHOD, "DashboardPage.logout"),
        }
        assert TraceabilityEdgeType.CALLS_METHOD in {e.edge_type for e in extended.edges}

    def test_bound_records_are_not_covered_no_workspace_path(self, tmp_path: Path) -> None:
        """A `"bound"` step-definition (reused from the tracked baseline)
        has no `workspace_path` — its own already-catalogued source is not
        read here (module docstring's own named scope boundary)."""
        req = _requirement("A")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "impact.feature").write_text(_IMPACT_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "impact.feature"),))
        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        automation_package = _automation_package(
            (_asset_record("user logs in", escalated=False),)  # outcome="bound", no workspace_path
        )
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        assert extended == graph  # nothing added

    def test_escalated_records_are_not_covered(self, tmp_path: Path) -> None:
        req = _requirement("A")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "impact.feature").write_text(_IMPACT_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "impact.feature"),))
        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        automation_package = _automation_package(
            (_asset_record("user logs in", escalated=True),)
        )
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        assert extended == graph  # nothing added

    def test_missing_generated_file_on_disk_is_skipped_not_a_crash(self, tmp_path: Path) -> None:
        req = _requirement("A")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "impact.feature").write_text(_IMPACT_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "impact.feature"),))
        graph = project_traceability_graph(requirement_set, package, features_root=features_root)

        automation_package = _automation_package(
            (_generated_asset_record("user logs in", "LoginSteps", "steps/Missing.java"),)
        )
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()  # the referenced file is never written

        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        assert extended == graph  # nothing added, no exception

    def test_is_deterministic(self, change_impact_fixture: _ImpactFixture) -> None:
        graph, automation_package, workspace_dir = change_impact_fixture

        extended_1 = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)
        extended_2 = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        assert extended_1 == extended_2

    def test_existing_completeness_queries_are_unaffected_by_the_extension(
        self, change_impact_fixture: _ImpactFixture
    ) -> None:
        """Adding PAGE_OBJECT_METHOD/CALLS_METHOD must not change what
        `evaluate_completeness`/`evaluate_binding_completeness` already
        compute over the SAME graph — proven directly, not assumed."""
        graph, automation_package, workspace_dir = change_impact_fixture

        base_completeness = evaluate_completeness(graph)
        base_binding = evaluate_binding_completeness(graph, automation_package)

        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        assert evaluate_completeness(extended) == base_completeness
        assert evaluate_binding_completeness(extended, automation_package) == base_binding


class TestChangeImpactQuery:
    """The delta-scoping payoff: given a changed method, exactly the
    affected scenarios — never more, never fewer."""

    def test_affected_scenarios_are_correctly_narrowed(
        self, change_impact_fixture: _ImpactFixture
    ) -> None:
        graph, automation_package, workspace_dir = change_impact_fixture
        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        login_impact = change_impact_for_method(extended, "LoginPage", "clickLogin")
        assert login_impact is not None
        assert login_impact.affected_scenario_ids == ("SCN-S1", "SCN-S2")
        assert login_impact.affected_scenario_count == 2

        logout_impact = change_impact_for_method(extended, "DashboardPage", "logout")
        assert logout_impact is not None
        assert logout_impact.affected_scenario_ids == ("SCN-S3",)
        assert "SCN-S1" not in logout_impact.affected_scenario_ids
        assert "SCN-S2" not in logout_impact.affected_scenario_ids

    def test_unknown_method_returns_none(self, change_impact_fixture: _ImpactFixture) -> None:
        graph, automation_package, workspace_dir = change_impact_fixture
        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        assert change_impact_for_method(extended, "NoSuchPage", "noSuchMethod") is None

    def test_query_against_unextended_graph_returns_none(
        self, change_impact_fixture: _ImpactFixture
    ) -> None:
        graph, _pkg, _ws_dir = change_impact_fixture

        assert change_impact_for_method(graph, "LoginPage", "clickLogin") is None

    def test_full_impact_map_covers_every_method(
        self, change_impact_fixture: _ImpactFixture
    ) -> None:
        graph, automation_package, workspace_dir = change_impact_fixture
        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)

        report = build_change_impact_report(extended)

        assert report.graph_id == extended.graph_id
        assert report.total_methods == 2
        by_method = {(m.class_name, m.method_name): m for m in report.method_impacts}
        assert by_method[("LoginPage", "clickLogin")].affected_scenario_ids == (
            "SCN-S1",
            "SCN-S2",
        )
        assert by_method[("DashboardPage", "logout")].affected_scenario_ids == ("SCN-S3",)

    def test_empty_graph_yields_empty_report(self) -> None:
        empty_graph = TraceabilityGraph(graph_id=graph_id_for("run-empty"), nodes=(), edges=())

        report = build_change_impact_report(empty_graph)

        assert report.total_methods == 0
        assert report.method_impacts == ()

    def test_report_structure_is_gate_ready_but_has_no_gating(self) -> None:
        report = ChangeImpactReport(
            graph_id="tg-000000000000",
            total_methods=1,
            method_impacts=(
                MethodImpact(
                    class_name="LoginPage",
                    method_name="clickLogin",
                    affected_scenario_count=1,
                    affected_scenario_ids=("SCN-1",),
                ),
            ),
        )
        assert report.total_methods == 1
        assert not hasattr(report, "passed")
        assert not hasattr(report, "verdict")
        assert not hasattr(report, "gate_status")

        import requirement_intelligence.traceability_graph as package

        assert not any(
            name in package.__all__
            for name in ("evaluate_gate", "check_threshold", "GateDecision", "GateResult")
        )


class TestModelInvariants:
    def test_graph_rejects_edge_to_absent_node(self) -> None:
        requirement_node = TraceabilityNode(
            node_id="tn-req",
            node_type=TraceabilityNodeType.REQUIREMENT,
            referenced_id="REQ-1",
            label="Requirement REQ-1",
        )
        dangling_edge = TraceabilityEdge(
            edge_id="te-dangling",
            edge_type=TraceabilityEdgeType.HAS_SCENARIO,
            source_node_id="tn-req",
            target_node_id="tn-missing-scenario",
            rationale="Requirement REQ-1 has scenario SCN-1.",
        )

        with pytest.raises(ValidationError, match="not present in this graph"):
            TraceabilityGraph(graph_id="tg-1", nodes=(requirement_node,), edges=(dangling_edge,))

    def test_report_rejects_mismatched_counts(self) -> None:
        with pytest.raises(ValidationError, match="must equal total_requirements"):
            CompletenessReport(
                graph_id="tg-1",
                total_requirements=5,
                tested_requirement_count=1,
                untested_requirement_count=1,  # 1 + 1 != 5
                coverage_percentage=20.0,
                untested_requirements=(),
            )

    def test_report_rejects_untested_list_length_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="must equal untested_requirement_count"):
            CompletenessReport(
                graph_id="tg-1",
                total_requirements=2,
                tested_requirement_count=1,
                untested_requirement_count=1,
                coverage_percentage=50.0,
                untested_requirements=(),  # length 0, but count says 1
            )

    def test_binding_report_rejects_mismatched_counts(self) -> None:
        with pytest.raises(ValidationError, match="must equal total_steps"):
            BindingCompletenessReport(
                graph_id="tg-1",
                total_steps=5,
                bound_step_count=1,
                unbound_step_count=1,  # 1 + 1 != 5
                coverage_percentage=20.0,
                unbound_steps=(),
            )

    def test_binding_report_rejects_unbound_list_length_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="must equal unbound_step_count"):
            BindingCompletenessReport(
                graph_id="tg-1",
                total_steps=2,
                bound_step_count=1,
                unbound_step_count=1,
                coverage_percentage=50.0,
                unbound_steps=(),  # length 0, but count says 1
            )

    def test_method_impact_rejects_mismatched_count(self) -> None:
        with pytest.raises(ValidationError, match="must equal affected_scenario_count"):
            MethodImpact(
                class_name="LoginPage",
                method_name="clickLogin",
                affected_scenario_count=2,
                affected_scenario_ids=("SCN-1",),  # length 1, but count says 2
            )

    def test_change_impact_report_rejects_mismatched_count(self) -> None:
        with pytest.raises(ValidationError, match="must equal total_methods"):
            ChangeImpactReport(
                graph_id="tg-1",
                total_methods=2,
                method_impacts=(
                    MethodImpact(
                        class_name="LoginPage",
                        method_name="clickLogin",
                        affected_scenario_count=0,
                        affected_scenario_ids=(),
                    ),
                ),  # length 1, but total_methods says 2
            )


class TestIdentityAndTraversal:
    def test_node_and_edge_ids_are_pure_functions(self) -> None:
        assert node_id_for("requirement", "REQ-1") == node_id_for("requirement", "REQ-1")
        assert node_id_for("requirement", "REQ-1") != node_id_for("requirement", "REQ-2")
        assert node_id_for("requirement", "REQ-1") != node_id_for("scenario", "REQ-1")

        edge_id = edge_id_for("has_scenario", "tn-a", "tn-b")
        assert edge_id == edge_id_for("has_scenario", "tn-a", "tn-b")
        assert edge_id != edge_id_for("has_scenario", "tn-b", "tn-a")

    def test_reachable_from_walks_directed_edges_only(self) -> None:
        edges = (
            TraceabilityEdge(
                edge_id="te-1",
                edge_type=TraceabilityEdgeType.HAS_SCENARIO,
                source_node_id="req",
                target_node_id="scn",
                rationale="r",
            ),
            TraceabilityEdge(
                edge_id="te-2",
                edge_type=TraceabilityEdgeType.HAS_STEP,
                source_node_id="scn",
                target_node_id="step",
                rationale="r",
            ),
        )
        adjacency = build_directed_adjacency(edges)

        assert reachable_from(adjacency, "req") == {"req", "scn", "step"}
        # Directed: nothing reaches back to "req" from "step".
        assert reachable_from(adjacency, "step") == {"step"}

    def test_reverse_adjacency_walks_edges_backward(self) -> None:
        edges = (
            TraceabilityEdge(
                edge_id="te-1",
                edge_type=TraceabilityEdgeType.HAS_SCENARIO,
                source_node_id="req",
                target_node_id="scn",
                rationale="r",
            ),
            TraceabilityEdge(
                edge_id="te-2",
                edge_type=TraceabilityEdgeType.HAS_STEP,
                source_node_id="scn",
                target_node_id="step",
                rationale="r",
            ),
            TraceabilityEdge(
                edge_id="te-3",
                edge_type=TraceabilityEdgeType.CALLS_METHOD,
                source_node_id="step",
                target_node_id="method",
                rationale="r",
            ),
        )
        reverse_adjacency = build_reverse_directed_adjacency(edges)

        # From "method", walking backward reaches every ancestor: step, scenario, requirement.
        assert reachable_from(reverse_adjacency, "method") == {"method", "step", "scn", "req"}
        # Directed in reverse: nothing reachable backward from "req" (it has no ancestors).
        assert reachable_from(reverse_adjacency, "req") == {"req"}


class TestSerialization:
    def test_renders_without_recomputing(
        self, four_requirement_fixture: _Fixture
    ) -> None:
        requirement_set, package, features_root = four_requirement_fixture
        graph = project_traceability_graph(requirement_set, package, features_root=features_root)
        report = evaluate_completeness(graph)

        graph_json = render_graph_json(graph)
        assert graph_json["graphId"] == graph.graph_id
        assert len(graph_json["nodes"]) == len(graph.nodes)

        report_json = render_completeness_json(report)
        assert report_json["totalRequirements"] == report.total_requirements
        assert report_json["coveragePercentage"] == report.coverage_percentage

        report_md = render_completeness_report(report)
        assert "Coverage: **25.00%**" in report_md
        assert "no_scenario" in report_md
        assert "scenario_without_steps" in report_md

        graph_md = render_graph_report(graph)
        assert "requirement" in graph_md
        assert "has_scenario" in graph_md

    def test_renders_binding_report_without_recomputing(self, tmp_path: Path) -> None:
        req = _requirement("A")
        requirement_set = _requirement_set([req])
        features_root = tmp_path / "features"
        features_root.mkdir()
        (features_root / "tested.feature").write_text(_TESTED_FEATURE, encoding="utf-8")
        package = _package((_feature_record(req.requirement_id, "tested.feature"),))
        graph = project_traceability_graph(requirement_set, package, features_root=features_root)
        automation_package = _automation_package(
            (
                _asset_record("a precondition", escalated=False),
                _asset_record("an action occurs", escalated=True),
            )
        )
        report = evaluate_binding_completeness(graph, automation_package)

        report_json = render_binding_completeness_json(report)
        assert report_json["totalSteps"] == report.total_steps
        assert report_json["coveragePercentage"] == report.coverage_percentage

        report_md = render_binding_completeness_report(report)
        assert "escalated" in report_md
        assert "no_step_definition_need" in report_md

    def test_renders_change_impact_report_without_recomputing(
        self, change_impact_fixture: _ImpactFixture
    ) -> None:
        graph, automation_package, workspace_dir = change_impact_fixture
        extended = project_change_impact(graph, automation_package, workspace_dir=workspace_dir)
        report = build_change_impact_report(extended)

        report_json = render_change_impact_json(report)
        assert report_json["totalMethods"] == report.total_methods
        assert report_json["graphId"] == report.graph_id

        report_md = render_change_impact_report(report)
        assert "LoginPage.clickLogin" in report_md
        assert "SCN-S1" in report_md
        assert "SCN-S2" in report_md
        assert "DashboardPage.logout" in report_md
        assert "SCN-S3" in report_md


class TestScopeDiscipline:
    def test_does_not_import_the_frozen_adr_0023_service(self) -> None:
        """Containment test, mirroring ADR-0023's own convention: this package
        reuses the Knowledge Graph *pattern*, never its code or its frozen
        runtime service."""
        package_dir = Path(__file__).resolve().parent.parent.parent / (
            "requirement_intelligence/traceability_graph"
        )
        source_files = sorted(package_dir.glob("*.py"))
        assert source_files, "expected the traceability_graph package to exist"

        for source_file in source_files:
            tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "knowledge_graph" not in alias.name, (
                            f"{source_file.name} imports {alias.name!r} -- "
                            "this package must not touch the frozen ADR-0023 service."
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "knowledge_graph" not in node.module, (
                        f"{source_file.name} imports from {node.module!r} -- "
                        "this package must not touch the frozen ADR-0023 service."
                    )
