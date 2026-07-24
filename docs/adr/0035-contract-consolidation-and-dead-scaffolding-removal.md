# ADR-0035 — Contract Consolidation and Dead Scaffolding Removal

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none. Evidentiary basis: direct verification performed for this ADR (commands and results in each item below), building on `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.2 and §4.3.
- **Depends on:** ADR-0034 (TestableRequirement Contract — `CanonicalRequirement`/`RequirementPackage` are recorded here for removal precisely because that ADR replaces the job they were built for).
- **Runtime status:** Not applicable. This ADR **records** four items for removal; **removal itself is a separate, future task**. No file is deleted, moved, or modified by this ADR — every constraint governing this task forbids touching any file outside `docs/`.

## Problem

`docs/audit/CODEBASE_AUDIT_2026-07-24.md` identified dead scaffolding — code that exists, is never used, and would mislead a reader searching for "the real contract" or "the real dependency list." Each item below was independently re-verified for this ADR, not merely carried forward from the audit.

## Decision

Record the following four items for removal. **Removal does not happen in this task.**

### 1. `SourceConnector` Protocol in `shared/contracts/base.py`

**Claim:** a `Protocol` named `SourceConnector` is defined at `shared/contracts/base.py:31-51` with zero implementers anywhere in the codebase; the real, implemented contract every connector actually satisfies is the `SourceConnector` `ABC` in `requirement_intelligence/connectors/base.py:14-112` (a different method set entirely: `get_source_id`/`get_source_name`/`validate_connection`/`fetch_raw_records`/`get_metadata`, versus the Protocol's `source`/`health_check()`/`fetch(**query)`).

**Re-verified for this ADR:** `grep -rn "SourceConnector" --include="*.py" .` (excluding `tests/`) returns exactly six hits: the Protocol's own definition (`shared/contracts/base.py:31`), the ABC's own definition (`requirement_intelligence/connectors/base.py:14`), the three concrete connectors' class declarations (`ZapConnector(SourceConnector)`, `JiraConnector(SourceConnector)`, `SonarQubeConnector(SourceConnector)` — all importing from `connectors.base`, never from `shared.contracts.base`), and two prose references in docstrings (`normalization_responsibility.py:107`, `validation_rule.py:116`) that name it only as an example of "the platform's other extensible framework contracts," not as an actual dependency. **Confirmed: the Protocol in `shared/contracts/base.py` has zero implementers.**

**CRITICAL — scoped narrowly:** `shared/contracts/base.py` also defines `Schema` (`shared/contracts/base.py:15-27`), the frozen, `extra="forbid"`, enum-by-value `pydantic.BaseModel` base class every canonical model in the platform inherits from — `CanonicalRequirement`, `ConsolidatedArtifact`, `SourceArtifact`, `ParsedResponse`, `AnalysisResult`, and the future `TestableRequirement` (ADR-0034) alike. **`Schema` MUST survive this removal.** Only the `SourceConnector` `Protocol` (lines 31-51) is recorded for removal; `Schema` (lines 15-27) is explicitly out of scope and must not be touched by whatever future task executes this removal.

### 2. `requirement_intelligence/models/canonical_requirement.py`

**Claim:** `CanonicalRequirement` and its nested `SourceRef` are defined here and never constructed anywhere outside this file.

**Re-verified for this ADR:** `grep -rln "CanonicalRequirement" --include="*.py" .` (excluding `tests/`) returns only `requirement_intelligence/models/canonical_requirement.py` (its own definition) and `requirement_intelligence/models/__init__.py` (a re-export). No call site constructs it. **Confirmed dead.**

**Salvage note:** `SourceRef` (`canonical_requirement.py:27-32` — `system: SourceSystem`, `external_id: str`, `url: str | None`) is a small, self-contained provenance pointer. Whether its shape suits `TestableRequirement`'s own provenance needs (ADR-0034, TBD section) is a candidate for the future Layer 2 LLD to evaluate — this ADR does not decide it, and removal of `canonical_requirement.py` should not proceed without that evaluation happening first, so a useful shape is not lost by deleting the file wholesale.

**Resolution note (additive only, ADR-0042).** The `SourceRef` salvage question is decided: ADR-0042 (TestableRequirement Field Specification, Decision 4) salvages `SourceRef` into `TestableRequirement`'s `traces_to[]`, using its actual field shape unchanged (`system`/`external_id`/`url`). **This item's removal is now unblocked** — it may proceed as a future task per this ADR's own governance line, citing ADR-0042 as the salvage record.

### 3. `requirement_intelligence/models/requirement_package.py`

**Claim:** `RequirementPackage` is defined here and never constructed anywhere.

**Re-verified for this ADR:** `grep -rln "RequirementPackage" --include="*.py" .` (excluding `tests/`) returns `requirement_intelligence/models/requirement_package.py` (its own definition), `requirement_intelligence/models/__init__.py` (re-export), `requirement_intelligence/models/consolidated_artifact.py` (a docstring cross-reference describing the *relationship* between the two models, not a construction), and `requirement_intelligence/consolidation/consolidation_engine.py:10`, whose only mention is the negative statement that the engine does **not** "build a `RequirementPackage`." **Confirmed dead**, and confirmed by its own neighboring code that it was never intended to be built by the one subsystem positioned to build it. ADR-0034 establishes `TestableRequirementSet` as its replacement; no salvage note applies — its own docstring names Azure OpenAI (an unimplemented provider stub) as its intended consumer, which does not carry forward.

### 4. The `jira` SDK dependency in `requirements.txt`

**Claim:** `requirements.txt` declares the official `jira` Python SDK, but the JIRA connector talks to the REST API directly via `httpx`, never importing it.

**Re-verified for this ADR:** `requirements.txt:27` reads `jira>=3.8,<4.0                  # Jira connector`. `grep -rn "^import jira\|^from jira" --include="*.py" .` across the entire repository returns **zero matches**. **Confirmed: declared, never imported.**

## D1 — Why removal is recorded, not executed, here

This task's governing constraint is documentation-only: no file outside `docs/` may be touched. Recording these four items now, with re-verified evidence and precise citations, means the future removal task has a ready-made, already-audited work list and does not need to re-derive the "is this actually dead" judgement from scratch — it only needs to execute the deletion (and, for item 2, resolve the `SourceRef` salvage question first).

## D2 — Why the `Schema` carve-out is called out this explicitly

`shared/contracts/base.py` contains both the dead `SourceConnector` Protocol and the platform-wide-used `Schema` base class in the same small file. A removal task working from a summary like "delete the dead contract in `shared/contracts/base.py`" without this ADR's explicit line-range distinction risks deleting the wrong half of the file. This ADR exists in part to prevent that specific, plausible mistake.

## Recommendations (permanent)

1. **Removal of items 1, 3, and 4 may proceed independently, in any order, once authorized as a future task.**
2. **Removal of item 2 (`canonical_requirement.py`) must not proceed until the `SourceRef` salvage question is resolved** by whoever designs Layer 2's LLD (ADR-0034 TBD section) — either by porting `SourceRef` into `TestableRequirement`'s own module first, or by explicitly deciding it is not needed.
3. **No new dependency is added to `requirements.txt` without a corresponding import existing in the same change** — the discipline this ADR's item 4 finding argues for going forward, not only backward.
4. **A future removal task is a bugfix-class change under ADR-0032's carve-out 4** (Layer 1 Capability Freeze) — it removes dead code, adds no new judgement capability, and does not require the freeze to be lifted.

## Ownership, scope, and governance

- **Owns:** the identification and removal record for these four dead-scaffolding items.
- **Does not own:** `Schema` (explicitly preserved, D2); the real `SourceConnector` ABC in `requirement_intelligence/connectors/base.py` (unaffected — it is the surviving contract, not a removal target); `TestableRequirement`'s eventual shape (ADR-0034 decides whether `SourceRef` is salvaged into it).
- **Governance:** Accepted as a removal record. Execution is a future task, authorized under ADR-0032 carve-out 4.
