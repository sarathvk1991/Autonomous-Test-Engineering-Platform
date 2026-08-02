"""Promotion's mechanism (ADR-0045 D5): copy into the tracked baseline, then
STAGE (never auto-commit).

Proves: `apply_promotion` writes the candidate's exact `java_source` at its
own resolved relative path under `src/test/java/`, creating parent
directories as needed; `stage_promoted_assets` `git add`s the written file
(git-visible, per D5) without ever committing it -- `git log` stays
unchanged, only the index gains a staged addition; and staging an empty
list is a true no-op (no git process spawned at all).
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from automation_engineering.promotion.identity import resolve_candidate_identity
from automation_engineering.promotion.mechanism import apply_promotion, stage_promoted_assets
from automation_engineering.promotion.models import Promoted, PromotionCandidate

pytestmark = pytest.mark.unit

_STEP_SOURCE = textwrap.dedent(
    """\
    package com.automation.steps;

    import io.cucumber.java.en.When;

    public class SearchProductSteps {

        @When("I search for a product")
        public void iSearchForAProduct() {
        }
    }
    """
)


def _run_git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run_git("init", "--quiet", cwd=root)
    _run_git("config", "user.email", "test@example.com", cwd=root)
    _run_git("config", "user.name", "Test", cwd=root)
    (root / ".gitkeep").write_text("", encoding="utf-8")
    _run_git("add", ".gitkeep", cwd=root)
    _run_git("commit", "--quiet", "-m", "initial", cwd=root)


def _promoted_candidate() -> Promoted:
    asset, relative_path = resolve_candidate_identity(_STEP_SOURCE)
    candidate = PromotionCandidate(
        java_source=_STEP_SOURCE, asset=asset, relative_path=relative_path
    )
    return Promoted(candidate=candidate)


class TestApplyPromotionWritesTheCandidateFile:
    def test_writes_exact_java_source_at_the_resolved_path(self, tmp_path: Path) -> None:
        baseline_root = tmp_path / "baseline"
        promoted = _promoted_candidate()

        written = apply_promotion(promoted, baseline_root)

        expected = baseline_root / "src/test/java/com/automation/steps/SearchProductSteps.java"
        assert written == expected
        assert written.read_text(encoding="utf-8") == _STEP_SOURCE

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        baseline_root = tmp_path / "baseline"
        assert not baseline_root.exists()

        apply_promotion(_promoted_candidate(), baseline_root)

        assert (baseline_root / "src/test/java/com/automation/steps").is_dir()


class TestStagingIsGitVisibleButNeverCommitted:
    def test_staged_file_appears_in_the_index_not_a_new_commit(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        _init_git_repo(repo_root)
        log_before = _run_git("log", "--oneline", cwd=repo_root).stdout

        promoted = _promoted_candidate()
        written = apply_promotion(promoted, repo_root)
        stage_promoted_assets([written], repo_root)

        status = _run_git("status", "--porcelain", cwd=repo_root)
        assert "A  src/test/java/com/automation/steps/SearchProductSteps.java" in status.stdout

        diff_cached = _run_git("diff", "--cached", "--name-only", cwd=repo_root)
        assert "src/test/java/com/automation/steps/SearchProductSteps.java" in diff_cached.stdout

        log_after = _run_git("log", "--oneline", cwd=repo_root).stdout
        assert log_after == log_before  # no new commit was created

    def test_empty_paths_never_spawns_a_git_process(self) -> None:
        with patch("automation_engineering.promotion.mechanism.subprocess.run") as mock_run:
            stage_promoted_assets([], Path("/does/not/matter"))

        mock_run.assert_not_called()
