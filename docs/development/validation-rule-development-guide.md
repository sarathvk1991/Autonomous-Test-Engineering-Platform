# Validation Rule Development Guide

| Attribute        | Value                                                                 |
| ---------------- | --------------------------------------------------------------------- |
| Document type    | Developer Engineering Guide                                           |
| Status           | Active                                                                 |
| Applies to       | Every concrete validation rule implemented in the Response Validation Framework |
| Supplements      | `docs/architecture/validation-rule-catalog.md`                        |
| Aligns with      | `docs/coding-standards.md` · `docs/naming-conventions.md`             |
| Audience         | Engineers implementing validation rules · Code reviewers              |

> **This is an engineering guide, not an architecture document.** It standardises
> *how* a validation rule is implemented in this codebase. It never redefines the
> architecture. Where this guide and the architecture appear to differ, the
> **architecture is the source of truth** and this guide is wrong and must be
> corrected.

---

## 1. Purpose

This document defines the engineering standards for implementing **validation
rules** — the single-concern checks executed by the Response Validation
Framework.

It exists so that every rule, written by any engineer at any time, is:

- **Architecture-conformant** — it obeys the Validation Rule Catalog.
- **Consistent** — it looks and behaves like every other rule.
- **Testable** — it ships with a complete, predictable test suite.
- **Reviewable** — a reviewer can check it against a fixed checklist.

It supplements `docs/architecture/validation-rule-catalog.md`. The catalog
defines **what** each rule is (identity, layer, single concern, severity,
blocking). This guide defines **how** to turn a catalogued rule into conforming,
tested, documented code.

---

## 2. Relationship to Architecture

The architecture is the source of truth. This guide only operationalises it.

| Question | Answered by | Document |
| -------- | ----------- | -------- |
| Does this rule exist, and what is its identity? | Architecture | `validation-rule-catalog.md` (§4, §9) |
| Which single concern does it own, and in which layer? | Architecture | `validation-rule-catalog.md` (§3, §8) |
| What severity and blocking capability does it carry? | Architecture | `validation-rule-catalog.md` (§14, §15) |
| What must its independence guarantees be? | Architecture | `validation-rule-catalog.md` (§16) |
| **How do I implement, test, document, and review it?** | **This guide** | this document |

> **Engineering rule**
> Never invent a rule in code. A rule must already exist in the catalog — with an
> approved Rule ID, layer, classification, severity, and blocking capability —
> **before** a line of its implementation is written. If the catalog does not
> define it, stop and take it through architecture governance
> (`validation-rule-catalog.md` §22) first.

The framework contracts this guide builds on are already implemented and frozen:

| Contract | Module |
| -------- | ------ |
| `ValidationRule` (abstract base) | `requirement_intelligence/validation/validation_rule.py` |
| `ValidationRuleMetadata` (identity) | `requirement_intelligence/validation/validation_rule_metadata.py` |
| `ValidationLayer` / `LAYER_ORDER` | `requirement_intelligence/validation/validation_rule_layer.py` |
| `ValidationIssue`, `ValidationSeverity` | `requirement_intelligence/validation/models/` |
| `ValidationRuleError` | `requirement_intelligence/validation/validation_exceptions.py` |

All of the above are re-exported from `requirement_intelligence.validation`.

---

## 3. Rule Development Workflow

Every rule follows the same five-stage workflow. Each stage has an exit
condition; do not advance until it is met.

```text
   Architecture ──► Implementation ──► Testing ──► Review ──► Completion
        │                 │               │           │            │
   rule exists in    one concern,    positive +   checklist    Definition
   the catalog       pure validate    negative +   passes      of Done met
   (ID, layer,       returning        edge +                   (§14)
   severity)         issues           metadata +
                                      immutability
```

| Stage | What happens | Exit condition |
| ----- | ------------ | -------------- |
| **Architecture** | Confirm the rule is catalogued and read its catalog entry. | The Rule ID, layer, severity, blocking, classification, and single concern are known and approved. |
| **Implementation** | Subclass `ValidationRule`; implement `metadata` and `validate`. | One concern only; pure, deterministic `validate`; returns `list[ValidationIssue]`. |
| **Testing** | Write the required unit tests (§11). | Positive, negative, edge, metadata, and immutability tests pass. |
| **Review** | A reviewer applies the checklist (§13). | Every checklist box is ticked. |
| **Completion** | Merge once the Definition of Done is met. | All of §14 satisfied; `ruff` and `mypy` clean. |

---

## 4. Rule File Structure

Rules live under a dedicated `rules/` subpackage of the validation framework.
**One rule per file.** Group files by layer so the directory mirrors the
pipeline order.

```text
requirement_intelligence/validation/rules/
├── __init__.py
├── _support.py                     # optional shared issue-building helpers
├── registration.py                 # assembles rule sets / registries
├── transport/
│   ├── __init__.py
│   ├── response_exists_rule.py     # TRANSPORT-0001  ResponseExistsRule
│   └── empty_response_rule.py      # TRANSPORT-0002  EmptyResponseRule
├── syntax/
│   ├── __init__.py
│   └── valid_structure_rule.py     # SYNTAX-0001     ValidStructureRule
├── schema/
├── structural/
├── content/
├── evidence/
├── traceability/
├── reasoning/
└── business/
```

Mirror the layout under tests:

```text
tests/unit/validation/rules/
├── transport/
│   ├── test_response_exists_rule.py
│   └── test_empty_response_rule.py
└── ...
```

**Conventions.**

- **File name** = `snake_case` of the rule name (`ResponseExistsRule` →
  `response_exists_rule.py`).
- **One public class per file** — the rule. Keep private helpers module-private
  (leading underscore) or in `_support.py` if shared.
- A rule **never imports another rule** (Validation Rule Catalog §17). It imports
  only framework contracts and shared utilities.
- Every module starts with `from __future__ import annotations`
  (`docs/coding-standards.md`).

---

## 5. Rule Naming Convention

A rule's **class name** is the catalog Rule Name: a concern-describing noun
phrase ending in `Rule` (Validation Rule Catalog §5).

| Use | Avoid |
| --- | ----- |
| `ResponseExistsRule` | `CheckResponse` |
| `RequiredSectionsRule` | `Rule1` |
| `DuplicateRequirementRule` | `ValidationRuleA` |

**Rules.**

- Name the **concern**, not the action: `ResponseExistsRule` (concern), never
  `CheckResponse` (action).
- The name must be **descriptive and unique**; opaque or sequential names
  (`Rule1`, `ValidationRuleA`) are prohibited — a reviewer must understand the
  rule from its name alone.
- The class name, the file name (`snake_case`), and the `rule_name` in metadata
  must all describe the same single concern and match the catalog entry.

---

## 6. Rule Responsibilities

> **Engineering rule**
> **Every rule validates exactly ONE concern — never multiple.** A rule that
> checks two things is two rules (Validation Rule Catalog §3).

**Conforming — one concern per rule.**

```python
# content/empty_requirement_rule.py  →  CONTENT-0001
class EmptyRequirementRule(ValidationRule):
    """Validates that no requirement is empty."""
    # validate() checks ONLY: is any requirement empty?
```

**Non-conforming — three concerns in one rule.**

```python
# DO NOT DO THIS — this is three rules pretending to be one
class WellFormedRequirementRule(ValidationRule):
    def validate(self, response):
        # checks empty  → belongs to CONTENT-0001
        # checks description → belongs to CONTENT-0003
        # checks confidence  → belongs to CONTENT-0004
        ...
```

Split the compound rule into the three catalogued single-concern rules
(`CONTENT-0001`, `CONTENT-0003`, `CONTENT-0004`). Each then fails, evolves, and is
reasoned about independently.

> **The "and" test.** If you can only describe a rule's responsibility using the
> word *and* ("checks X **and** Y"), it is too large. Split it.

---

## 7. Rule Metadata

A rule exposes its identity through the `metadata` property, returning an
immutable `ValidationRuleMetadata`. Every value comes from the rule's **catalog
entry** — never invented in code.

| `ValidationRuleMetadata` field | Meaning | Where the value comes from |
| ------------------------------ | ------- | -------------------------- |
| `rule_id` | Stable identity (`<LAYER>-NNNN`) | Catalog §4, §9 (the rule's row) |
| `rule_name` | Concern-describing name | Catalog §5, §9 (the Name column) |
| `validation_layer` | The one layer the rule belongs to | Catalog §8 (the rule's layer) |
| `rule_version` | This rule's definition version (default `1.0.0`) | Catalog §20 (Rule Version) |
| `enabled` | Whether the rule participates when registered | Operational default `True`; toggled by configuration, not by the rule |
| `tags` *(reserved)* | Classification labels | Reserved — leave default |
| `documentation_reference` *(reserved)* | Pointer to docs | Reserved — leave default |
| `validation_contract_version` *(reserved)* | Targeted semantics version | Reserved — leave default |
| `future_schema_compatibility` *(reserved)* | Schema-evolution marker | Reserved — leave default |

> **Note — two kinds of "metadata".** The catalog entry (catalog §6) carries
> richer architectural metadata (Purpose, Classification, Stability, **Severity**,
> **Blocking**, Owner, …). The runtime `ValidationRuleMetadata` carries only
> **identity** (id, name, layer, version, enabled). **Severity and blocking are
> not on the metadata object** — they are decided per finding, on each
> `ValidationIssue` the rule emits (§9), exactly as the catalog assigns them.

**Conforming metadata.**

```python
from requirement_intelligence.validation import (
    ValidationLayer,
    ValidationRule,
    ValidationRuleMetadata,
)


class ResponseExistsRule(ValidationRule):
    @property
    def metadata(self) -> ValidationRuleMetadata:
        return ValidationRuleMetadata(
            rule_id="TRANSPORT-0001",
            rule_name="ResponseExistsRule",
            validation_layer=ValidationLayer.TRANSPORT,
            rule_version="1.0.0",
        )
```

Construct the metadata once and return the same value on every access. The legacy
convenience accessors (`rule_id`, `rule_name`, `validation_layer`, `rule_version`,
`enabled`) are provided by the base class reading through `metadata`; **do not**
override them.

---

## 8. Validation Logic

The `validate` method is the only place logic lives. It must satisfy every Rule
Independence guarantee (Validation Rule Catalog §16).

> **The `response` is a `ValidationInput` (ADR-0003).** At runtime, `validate`
> receives the canonical `ValidationInput` — the binding of the analysed response and
> its normalization output. The abstract contract stays `response: Any` (unchanged),
> but rules read through it:
> - **Transport** rules read `response.analysis_result` (the `LLMResponse`, delivery
>   facts, `execution_id`).
> - **Syntax** rules read `response.normalization_result.parsed_response.normalization_outcome`
>   (`SYNTAX-0001`) and `response.normalization_result.observations`
>   (`SYNTAX-0002`/`SYNTAX-0003`).
> - **Schema onward** read `response.normalization_result.parsed_response.normalized_structure`.
>
> Rules never parse, normalize, copy, or re-derive structure — they read the shared
> `ParsedResponse` the handoff already produced.

| Property | Engineering meaning |
| -------- | ------------------- |
| **Pure function** | Output depends only on the `response` argument — nothing else. |
| **Deterministic** | The same `response` always yields the same finding set. |
| **Stateless** | No instance state persists between calls; no module-level mutable state. |
| **No mutation** | The `response` is read-only; never modify, repair, or reshape it. |
| **No side effects** | No I/O, no logging of payloads, no network, no persistence, no clock-driven branching. |

```python
from typing import Any

from requirement_intelligence.validation import ValidationIssue, ValidationSeverity


class ResponseExistsRule(ValidationRule):
    # ... metadata as above ...

    def validate(self, response: Any) -> list[ValidationIssue]:
        # Read-only inspection via the ValidationInput (ADR-0003).
        analysis_result = response.analysis_result
        if analysis_result.llm_response.generated_text.strip():
            return []  # concern satisfied → no findings
        return [self._missing_response_issue(analysis_result)]
```

**Determinism boundary.** Determinism applies to the **finding content** — the
`category`, `severity`, `validation_layer`, `location`, `message`,
`recommendation`, and `blocking` of each issue. Surrogate fields are observational
metadata and are derived, not invented:

- `correlation_id` — derive from the response's execution identity
  (e.g. `response.analysis_result.execution_id`), so it is stable for a given
  response.
- `created_at` — a timestamp; the **one** inherently time-varying field. Keep it
  out of any equality or identity logic, and exclude it from test assertions
  (§11). It never affects the finding.
- `issue_id` — prefer a **content-derived, stable** value (for example, composed
  from `rule_id` and `location`) so re-running yields identical issues.

> **Engineering rule**
> A rule must never read the clock, the environment, configuration globals, or
> another rule to decide its finding. If correctness depends on anything other
> than the `response`, the rule is non-conforming.

---

## 9. Rule Outputs

> **A rule returns a `list[ValidationIssue]` — and nothing else.**

| The rule returns | The rule never returns |
| ---------------- | ---------------------- |
| `list[ValidationIssue]` (possibly empty) | a `ValidationResult` |
| an empty list when the concern is satisfied | a verdict, summary, or statistics |
| one issue per observed occurrence of its single concern | pipeline state or execution context |

- **Empty list = pass.** Returning `[]` means the rule observed nothing worth
  recording. This is the normal, common case.
- **One issue per occurrence.** A rule may emit several issues if its single
  concern occurs several times (e.g. three empty requirements → three issues),
  but every issue is the *same* concern.
- Each `ValidationIssue` carries the **severity and blocking** the catalog assigns
  to this rule (catalog §14, §15). A foundational rule whose concern makes the
  response unprocessable emits `CRITICAL` / `blocking=True`; a semantic rule
  records its finding and does not block.

```python
from datetime import datetime, timezone

from requirement_intelligence.validation import ValidationIssue, ValidationSeverity


def _missing_response_issue(self, analysis_result: Any) -> ValidationIssue:
    return ValidationIssue(
        issue_id=f"{self.rule_id}#response",
        category="transport",
        severity=ValidationSeverity.CRITICAL,
        validation_layer=self.validation_layer,
        rule_id=self.rule_id,
        rule_version=self.rule_version,
        message="No response content was received.",
        location="$",
        recommendation="Ensure the analysis produced a non-empty response.",
        blocking=True,
        correlation_id=analysis_result.execution_id,
        created_at=datetime.now(timezone.utc),
    )
```

Assembling these issues into a `ValidationResult` is the **framework's** job, not
the rule's. The rule never sees the pipeline, the registry, or other rules' output.

---

## 10. Error Handling

A rule distinguishes a **finding** (a normal outcome, returned) from a **failure**
(the rule itself could not run, raised).

| Situation | What the rule does |
| --------- | ------------------ |
| The concern is violated | **Return** a `ValidationIssue` — this is a finding, not an error. |
| The concern is satisfied | **Return** `[]`. |
| Expected-absent data (e.g. an optional section is missing) | Treat as a finding or a pass per the catalog concern — **never** raise. |
| A genuine internal defect (an impossible state the rule cannot interpret) | **Raise** `ValidationRuleError`. |

```python
from requirement_intelligence.validation import ValidationRuleError
```

**Rules.**

- **Never raise for a normal validation outcome.** A violated concern is returned
  as an issue; a satisfied concern returns `[]`.
- **Never swallow a genuine defect.** If the rule reaches a state it cannot
  reasonably interpret, raise `ValidationRuleError` with a clear message — the
  framework surfaces it as an infrastructure failure, distinct from any verdict.
- **Never raise a bare `Exception`** (`docs/coding-standards.md`); use the typed
  `ValidationRuleError`.
- **Be defensive about shape, not about meaning.** Guard against missing fields
  the canonical input guarantees only when their absence is a genuine impossible
  state; otherwise model absence as a finding.

---

## 11. Unit Testing Standard

Every rule ships with a unit test module (`@pytest.mark.unit`, no real I/O —
`docs/coding-standards.md`). The following tests are **required**.

| Test | What it asserts |
| ---- | --------------- |
| **Positive case** | A response satisfying the concern yields `[]`. |
| **Negative case** | A response violating the concern yields exactly the expected issue(s), with the correct `severity`, `validation_layer`, `blocking`, and `message` intent. |
| **Edge cases** | Boundary inputs (empty collections, whitespace-only, minimal/maximal sizes, multiple occurrences) behave correctly. |
| **Metadata** | `rule_id`, `rule_name`, `validation_layer`, and `rule_version` match the catalog entry exactly. |
| **Immutability / purity** | `validate` does not mutate the response, and repeated calls on the same response return equal finding sets (determinism). |

```python
import pytest

from requirement_intelligence.validation import ValidationLayer, ValidationSeverity


@pytest.mark.unit
class TestResponseExistsRule:
    def test_metadata_matches_catalog(self) -> None:
        rule = ResponseExistsRule()
        assert rule.rule_id == "TRANSPORT-0001"
        assert rule.rule_name == "ResponseExistsRule"
        assert rule.validation_layer == ValidationLayer.TRANSPORT
        assert rule.rule_version == "1.0.0"

    def test_positive_case_returns_no_issues(self) -> None:
        rule = ResponseExistsRule()
        assert rule.validate(_response_with_text("a verdict")) == []

    def test_negative_case_returns_one_critical_blocking_issue(self) -> None:
        rule = ResponseExistsRule()
        issues = rule.validate(_response_with_text(""))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL
        assert issues[0].blocking is True
        assert issues[0].validation_layer == ValidationLayer.TRANSPORT

    def test_validate_does_not_mutate_response(self) -> None:
        rule = ResponseExistsRule()
        response = _response_with_text("a verdict")
        before = response.model_copy(deep=True)
        rule.validate(response)
        assert response == before

    def test_validate_is_deterministic(self) -> None:
        rule = ResponseExistsRule()
        response = _response_with_text("")
        first = [i.message for i in rule.validate(response)]
        second = [i.message for i in rule.validate(response)]
        assert first == second
```

**Testing rules.**

- Build test inputs in-memory; never call a provider or perform I/O.
- Compare on **finding content** (`severity`, `layer`, `location`, `message`,
  `blocking`), never on `created_at`.
- One assertion concern per test method, mirroring one-concern-per-rule.

---

## 12. Documentation Standard

Every rule's **class docstring** must contain the seven sections of the **Rule
Documentation Contract** (Validation Rule Catalog §8 / the `ValidationRule`
module docstring). This is documentation only — there is no runtime enforcement —
but it is required for review.

| Section | Documents |
| ------- | --------- |
| **Purpose** | The single concern the rule validates. |
| **Layer** | Which `ValidationLayer` the rule belongs to. |
| **Inputs** | What part of the response the rule reads. |
| **Outputs** | What findings the rule can produce (severity, blocking). |
| **Failure Conditions** | The conditions under which the rule raises a finding. |
| **Worked Example** | A concrete passing case and a concrete failing case. |
| **Architecture Reference** | The catalog Rule ID and governing section. |

```python
class ResponseExistsRule(ValidationRule):
    """Validate that the analysed response carries content.

    Purpose:
        Confirm a usable response was received (its single concern).
    Layer:
        Transport.
    Inputs:
        Reads the analysed response's generated content only; read-only.
    Outputs:
        One CRITICAL, blocking ValidationIssue when no content is present;
        otherwise no findings.
    Failure Conditions:
        Raises ValidationRuleError only on a genuine, uninterpretable internal
        state — never for a normal validation outcome.
    Worked Example:
        Pass: response carries "Refunds require manager approval." → [].
        Fail: response carries "" → one CRITICAL blocking issue.
    Architecture Reference:
        TRANSPORT-0001, Validation Rule Catalog §9.1.
    """
```

Module and public-symbol docstrings explain the **contract and why**, not
line-by-line behaviour (`docs/coding-standards.md`).

---

## 13. Code Review Checklist

A reviewer must confirm every box before approving a rule.

- [ ] **Catalogued first** — the Rule ID exists in the catalog with an approved
  layer, severity, classification, and blocking capability.
- [ ] **One concern** — the rule validates exactly one concern (no "and").
- [ ] **Correct layer** — `validation_layer` matches the catalog.
- [ ] **Naming** — class, file (`snake_case`), and `rule_name` all describe the
  one concern and match the catalog Name; no opaque/sequential names.
- [ ] **Metadata complete and sourced** — every `ValidationRuleMetadata` value
  comes from the catalog; convenience accessors are not overridden.
- [ ] **Pure `validate`** — deterministic, stateless, no mutation, no side
  effects, depends only on `response`.
- [ ] **Correct output** — returns `list[ValidationIssue]` (empty = pass); never
  a `ValidationResult` or pipeline state.
- [ ] **Correct severity/blocking** — each issue carries the catalog's severity
  and blocking capability.
- [ ] **No rule-to-rule dependency** — imports no other rule; relies only on the
  pipeline's layer ordering.
- [ ] **Error handling** — findings are returned, not raised; genuine defects
  raise `ValidationRuleError`, never bare `Exception`.
- [ ] **Tests complete** — positive, negative, edge, metadata, and
  immutability/determinism tests all present and passing.
- [ ] **Docstring complete** — all seven Rule Documentation Contract sections.
- [ ] **Tooling clean** — `ruff` and `mypy --strict` pass.

---

## 14. Definition of Done

A rule is complete **only** when every item below holds. Partial completion is
not done.

| Criterion | Met when |
| --------- | -------- |
| **Architecture conformant** | The rule matches its catalog entry exactly (identity, layer, one concern, severity, blocking) and depends on no other rule. |
| **Metadata complete** | `ValidationRuleMetadata` is fully populated from the catalog; identity accessors are inherited, not overridden. |
| **Tests complete** | Positive, negative, edge, metadata, and immutability/determinism tests pass under `pytest`. |
| **Documentation complete** | The class docstring contains all seven Rule Documentation Contract sections. |
| **Ruff clean** | `ruff check` (and `ruff format`) report no issues; `mypy --strict` passes. |

> **Definition of Done**
> A validation rule is done when it is **architecture-conformant, metadata-complete,
> test-complete, documentation-complete, and `ruff`-clean** — and the code review
> checklist (§13) is fully ticked. Until all five hold, the rule is in progress.

---

## 15. Future Guidance

The following are **reserved** capabilities defined by the architecture
(Validation Rule Catalog §23). They are **not** implemented today; do not build
them ahead of an approved architecture extension. When they arrive, they extend —
never replace — the standards in this guide.

| Reserved capability | What it will mean for rule development | Constraint that still holds |
| ------------------- | -------------------------------------- | --------------------------- |
| **Composite Rules** | A higher-order concern expressed over several findings. | Each underlying concern remains its own single-responsibility rule; composition never merges concerns. |
| **Parameterized Rules** | A rule whose thresholds are configurable. | Parameters tune one concern; they never let one rule cover several. The rule stays pure and deterministic for fixed parameters. |
| **AI-assisted Rules** | A rule whose evaluation is itself model-assisted. | Must remain deterministic in verdict, independent, non-mutating, and side-effect-free at the contract boundary; governed identity like any rule. |

> Until these are approved and specified, implement only single-concern,
> deterministic, stateless rules as defined in §6–§9.

---

## Appendix — Engineering Standards at a Glance

| # | Standard | Section |
| - | -------- | ------- |
| 1 | A rule is implemented only after it is catalogued. | §2, §3 |
| 2 | One rule per file, grouped by layer under `rules/`. | §4 |
| 3 | Class/file/`rule_name` describe one concern; end in `Rule`. | §5 |
| 4 | Exactly one concern per rule — no "and". | §6 |
| 5 | Metadata is fully sourced from the catalog; identity accessors inherited. | §7 |
| 6 | `validate` is pure, deterministic, stateless, non-mutating, side-effect-free. | §8 |
| 7 | Output is `list[ValidationIssue]` only (empty = pass). | §9 |
| 8 | Findings are returned; genuine defects raise `ValidationRuleError`. | §10 |
| 9 | Positive, negative, edge, metadata, immutability tests are required. | §11 |
| 10 | The class docstring carries all seven documentation sections. | §12 |
| 11 | Review against the §13 checklist; merge only at Definition of Done (§14). | §13, §14 |
| 12 | Reserved capabilities are not built ahead of architecture. | §15 |

> **Final note.** This guide standardises implementation; it does not define
> architecture. Every standard here is downstream of, and subordinate to,
> `docs/architecture/validation-rule-catalog.md` and the frozen framework
> contracts. If the architecture evolves (through an approved ADR), update this
> guide to follow it — never the reverse.
