"""Determinism tests for contracts.id_generation (ADR-0042 Decision 2).

Every REQ-*/AC-*/RSK-* id must be a pure function of already-computed inputs:
identical input yields an identical id across processes and runs, with no
coordination; changed input yields a changed id.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from contracts.id_generation import (
    compute_content_hash,
    generate_acceptance_criterion_id,
    generate_requirement_id,
    generate_risk_id,
    normalize,
)


@pytest.mark.unit
class TestNormalize:
    def test_casefolds(self) -> None:
        assert normalize("Account Must Lock") == normalize("account must lock")

    def test_collapses_whitespace(self) -> None:
        assert normalize("account   must\tlock") == normalize("account must lock")

    def test_strips_punctuation(self) -> None:
        assert normalize("Account must lock!") == normalize("Account must lock")

    def test_strips_leading_trailing_whitespace(self) -> None:
        assert normalize("  account must lock  ") == "account must lock"


@pytest.mark.unit
class TestRequirementId:
    def test_identical_input_yields_identical_id(self) -> None:
        a = generate_requirement_id("Account must lock after 5 attempts", ["PROJ-1"])
        b = generate_requirement_id("Account must lock after 5 attempts", ["PROJ-1"])
        assert a == b

    def test_formatting_differences_yield_identical_id(self) -> None:
        a = generate_requirement_id("Account must lock after 5 attempts!", ["PROJ-1"])
        b = generate_requirement_id("  ACCOUNT   MUST lock after 5 attempts", ["PROJ-1"])
        assert a == b

    def test_changed_title_yields_changed_id(self) -> None:
        a = generate_requirement_id("Account must lock after 5 attempts", ["PROJ-1"])
        b = generate_requirement_id("Account must lock after 10 attempts", ["PROJ-1"])
        assert a != b

    def test_changed_sources_yields_changed_id(self) -> None:
        a = generate_requirement_id("Account must lock after 5 attempts", ["PROJ-1"])
        b = generate_requirement_id("Account must lock after 5 attempts", ["PROJ-2"])
        assert a != b

    def test_source_order_does_not_affect_id(self) -> None:
        a = generate_requirement_id("Account must lock", ["PROJ-2", "PROJ-1"])
        b = generate_requirement_id("Account must lock", ["PROJ-1", "PROJ-2"])
        assert a == b

    def test_shape(self) -> None:
        req_id = generate_requirement_id("Account must lock", ["PROJ-1"])
        assert req_id.startswith("REQ-")
        assert len(req_id) == len("REQ-") + 8

    def test_deterministic_across_processes(self) -> None:
        script = (
            "from contracts.id_generation import generate_requirement_id;"
            "print(generate_requirement_id('Account must lock after 5 attempts', ['PROJ-1']))"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            cwd=".",
        )
        in_process = generate_requirement_id("Account must lock after 5 attempts", ["PROJ-1"])
        assert result.stdout.strip() == in_process


@pytest.mark.unit
class TestRiskId:
    def test_identical_input_yields_identical_id(self) -> None:
        a = generate_risk_id("Brute force risk", ["PROJ-1"])
        b = generate_risk_id("Brute force risk", ["PROJ-1"])
        assert a == b

    def test_changed_statement_yields_changed_id(self) -> None:
        a = generate_risk_id("Brute force risk", ["PROJ-1"])
        b = generate_risk_id("Injection risk", ["PROJ-1"])
        assert a != b

    def test_shape(self) -> None:
        risk_id = generate_risk_id("Brute force risk", ["PROJ-1"])
        assert risk_id.startswith("RSK-")
        assert len(risk_id) == len("RSK-") + 8

    def test_requirement_and_risk_ids_are_independent_namespaces(self) -> None:
        # Same normalized text + sources can legitimately mint different-prefixed
        # ids without collision risk, since REQ-/RSK- are visually and
        # structurally distinct namespaces.
        req_id = generate_requirement_id("Brute force risk", ["PROJ-1"])
        risk_id = generate_risk_id("Brute force risk", ["PROJ-1"])
        assert req_id.removeprefix("REQ-") == risk_id.removeprefix("RSK-")


@pytest.mark.unit
class TestAcceptanceCriterionId:
    def test_shape(self) -> None:
        ac_id = generate_acceptance_criterion_id("REQ-8d1fc3e1", 1)
        assert ac_id == "AC-8d1fc3e1-01"

    def test_ordinal_is_two_digit_zero_padded(self) -> None:
        assert generate_acceptance_criterion_id("REQ-abc12345", 3) == "AC-abc12345-03"
        assert generate_acceptance_criterion_id("REQ-abc12345", 12) == "AC-abc12345-12"

    def test_stable_within_requirement(self) -> None:
        first = generate_acceptance_criterion_id("REQ-abc12345", 1)
        second = generate_acceptance_criterion_id("REQ-abc12345", 1)
        assert first == second

    def test_different_ordinal_yields_different_id(self) -> None:
        first = generate_acceptance_criterion_id("REQ-abc12345", 1)
        second = generate_acceptance_criterion_id("REQ-abc12345", 2)
        assert first != second


@pytest.mark.unit
class TestContentHash:
    def test_identical_json_yields_identical_hash(self) -> None:
        payload = '{"a":1,"b":2}'
        assert compute_content_hash(payload) == compute_content_hash(payload)

    def test_changed_json_yields_changed_hash(self) -> None:
        assert compute_content_hash('{"a":1}') != compute_content_hash('{"a":2}')

    def test_is_full_sha256_hex_digest(self) -> None:
        digest = compute_content_hash("{}")
        assert len(digest) == 64
        int(digest, 16)  # raises ValueError if not valid hex
