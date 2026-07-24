# ADR-0033 — Naming Disambiguation and Package Renames

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing. Existing Accepted ADRs that reference the old package names (ADR-0017 "Quality Governance Framework," and every ADR/document citing `requirement_intelligence/quality_governance/` or `requirement_intelligence/execution/`) are **not edited** — this ADR is the canonical old-name → new-name mapping going forward (D3).
- **Governing design:** none. Evidentiary basis: `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.7/§2.8 (the two naming collisions) and §3.2, independently re-verified for this ADR.
- **Depends on:** ADR-0031 (Authoritative Layer Model — the new top-level names align with its Layer 4/Layer 5 names); ADR-0017 (Quality Governance Framework — the subsystem being renamed); ADR-0032 (Layer 1 Capability Freeze — this rename is one of its explicit carve-outs).
- **Runtime status:** Not applicable, and **not yet actioned**. This ADR *records* a locked mapping. No file is renamed, moved, or deleted by this ADR — every constraint governing this task forbids touching any file outside `docs/`. The rename itself is deferred to a future implementation task executed under ADR-0032's carve-out 3.

## Problem

Re-verified directly (`grep`/`Read` against the current repository, 2026-07-24): two names each currently identify two unrelated things.

- **"Quality Governance"** names both the empty top-level placeholder `quality_governance/` (ADR-0031's Layer 4, "Suite Quality Governance" — validates generated BDD/automation code, not started) and `requirement_intelligence/quality_governance/` (real, live, governed by ADR-0017 — the terminal release-decision authority for *one Requirement Intelligence run*, consuming only `GroundingResult`/`ValidationResult`/`CP1Result`). Neither knows the other exists.
- **"Execution"** names both the empty top-level placeholder `execution/` (ADR-0031's Layer 5, "Test Execution" — runs the generated suite, not started) and `requirement_intelligence/execution/` (real, live — the artifact/manifest-writing package for one Requirement Intelligence run, documented in `docs/architecture/execution-package.md`).

A reader — human or AI — searching this codebase for "quality governance" or "execution" cannot tell which of two unrelated subsystems is meant without opening the code. This has already produced confusion once (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.7/§2.8 exists specifically to disambiguate it for that audit).

## Decision

Lock the following package rename mapping. **Package paths only** — this ADR does not rename any class, module-internal identifier, or output artifact filename (D2).

| Old path | New path | Why |
|---|---|---|
| `requirement_intelligence/quality_governance/` | `requirement_intelligence/requirement_quality_governance/` | Disambiguates from the top-level placeholder; "requirement" names precisely what it governs — one Requirement Intelligence run's release decision. |
| `requirement_intelligence/execution/` | `requirement_intelligence/execution_package/` | Disambiguates from the top-level placeholder; matches the name already used in prose throughout the repository (`docs/architecture/execution-package.md`, "the Execution Package"). |
| `quality_governance/` (top level) | `suite_quality_governance/` | Aligns with ADR-0031's Layer 4 name, "Suite Quality Governance" — validates the generated BDD/automation *suite*, never a single requirement-analysis run. |
| `execution/` (top level) | `test_execution/` | Aligns with ADR-0031's Layer 5 name, "Test Execution" — runs the generated *test* suite, never a Requirement Intelligence run's own artifact writer. |

### Explicit non-scope

- **Output artifact filenames are not renamed by this decision.** `quality_governance_result.json`, `quality_governance_report.md`, `quality_governance_summary.md`, and every other artifact filename the Execution Package writes today keep their names exactly as-is. `manifest.json` carries SHA-256 checksums and the `generatedArtifacts` index keyed by those filenames (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.4); renaming artifacts is a separate, future Execution Package version bump — a decision this ADR does not make and does not imply.
- **No class, function, or model name is renamed by this decision.** `QualityGovernanceService`, `QualityGovernanceResult`, `ExecutionWriter`, etc. are unaffected; only the two containing package directories move.
- **Accepted ADRs that reference the old paths are not edited.** ADR-0017 continues to say `requirement_intelligence/quality_governance/` throughout its own body, because it is a historical record of a decision made under that name. **This ADR is the canonical mapping a reader consults** to translate any old-name citation, in ADR-0017 or elsewhere, to its current path.

## D1 — Why package paths only, not artifacts or class names

Renaming an output artifact filename changes a durable, checksummed, cross-run contract (the manifest's `generatedArtifacts` index) — a change with its own compatibility surface, orthogonal to fixing a source-tree naming collision. Renaming a class name is a larger, higher-risk refactor that touches every call site, test, and docstring referencing it. Scoping this decision to package paths alone delivers the disambiguation this ADR exists for — a reader can now tell the two "Quality Governance"s and two "Execution"s apart by path alone — without bundling in either of those larger, separable changes.

## D2 — Why the top-level names are chosen to match ADR-0031's layer names

`suite_quality_governance/` and `test_execution/` are not arbitrary; they are the snake_case form of ADR-0031's own Layer 4 ("Suite Quality Governance") and Layer 5 ("Test Execution") names. Choosing any other name would reintroduce exactly the kind of drift between a layer's governing ADR and its code location that this ADR exists to close.

## D3 — Why history is not retro-edited

Accepted ADRs are permanent records of a decision made at a point in time, under the name that existed then. Editing ADR-0017 to say `requirement_quality_governance/` would misrepresent what CAP-080's authors actually named and built. Instead, this ADR is the **single, canonical translation table** — any future reader who encounters `requirement_intelligence/quality_governance/` in an old ADR, docstring, or test consults this ADR to find its current location, exactly as a repository would consult a redirect table after a package move.

## Recommendations (permanent)

1. **All future ADRs, tickets, and specs use the disambiguated names** (`requirement_quality_governance`, `execution_package`, `suite_quality_governance`, `test_execution`) — never the old, colliding names, effective immediately for new documents.
2. **The actual filesystem rename is a separate implementation task**, executed under ADR-0032's carve-out 3, and must update every import, test, and doc citation atomically in that one change — not accrue as a partial rename.
3. **No further package-name collision is introduced without a disambiguation ADR of this kind first.** Naming a new top-level or `requirement_intelligence`-internal package after an existing name is out of policy.

## Ownership, scope, and governance

- **Owns:** the canonical old-name → new-name mapping for these four package paths.
- **Does not own:** the actual rename execution (future implementation task); any output artifact filename or manifest schema (unchanged); any class or model name (unchanged); the layer names it aligns to (ADR-0031).
- **Governance:** Accepted. Effective as the canonical mapping immediately; effective as a filesystem change only once the future rename task lands.
