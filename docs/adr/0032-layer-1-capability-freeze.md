# ADR-0032 — Layer 1 Capability Freeze

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none — this ADR is the governing decision. Evidentiary basis: `docs/audit/CODEBASE_AUDIT_2026-07-24.md`, and the commit-history verification in Stage 0 below, re-run for this ADR.
- **Depends on:** ADR-0031 (Authoritative Layer Model — defines Layer 1 and Layers 2–7 this freeze protects the boundary between); every Accepted Layer 1 subsystem ADR (ADR-0011–ADR-0019, ADR-0021–ADR-0030) — their runtime contracts are unaffected; their future growth is what this ADR bounds.
- **Runtime status:** Not applicable. This is a **documentation-only, policy** milestone: it authorizes no code change and forbids none that isn't already unbuilt. It changes no `PlatformContext` method, model, or version constant.

## Problem

`docs/audit/CODEBASE_AUDIT_2026-07-24.md` established that Requirement Intelligence (Layer 1, under ADR-0031) is FUNCTIONAL end to end, while Layers 2 through 7 are NOT STARTED or, at best, SCAFFOLDED. A verification re-run for this ADR (`git rev-list --count HEAD`, and `git log --oneline -- <path> | wc -l` per top-level directory) confirms the shape of that gap precisely:

| Scope | Commits touching it |
|---|---|
| Total commits on `main` | **252** |
| `requirement_intelligence/` | **142** (56% of all commits) |
| `docs/` | 183 (overlaps with the row above — many commits touch both a code change and its governing ADR together) |
| `shared/` or `infrastructure/` | 7 |
| `app/` | 3 |
| The six Layer 2–7 placeholder packages combined (`feature_engineering/`, `automation_engineering/`, `quality_governance/`, `execution/`, `failure_intelligence/`, `governance_dashboard/`) | **1** — the initial scaffold commit, with zero commits since |

**Verification note (additive only).** `docs/audit/CODEBASE_AUDIT_2026-07-24.md` (this ADR's
evidentiary basis) separately contained a genuine commit-count error ("1290" total /
"~1260" since the initial commit — corrected in that document's own Appendix, verified
against commit `932f416`). **This ADR's own table above does not share that error.** It was
independently re-run for this ADR (per the "Governing design" line above) rather than cited
from the audit, and its figure — 252 — was re-verified during the audit-correction pass: it
matches `git rev-list --count` at this ADR's own parent commit exactly (this ADR's own commit,
`4613b40`, is commit 253; 252 is the count immediately before it landed, the same
before-this-commit convention the audit itself used for its "last 5 commits" list). No change
to this table, and no change to this ADR's decision, is required.

More than half of the repository's entire commit history went into deepening Layer 1 — adding Requirement Enhancement, Grounding, Quality Governance (the requirement-analysis kind), Recommendation, Continuous Improvement, Knowledge Graph, Organizational Memory, and Learning, each behind its own multi-milestone ADR arc — while the platform has, to date, **never generated a feature file, never generated a page object, and never executed a test.** Left unaddressed, nothing structurally prevents this pattern from continuing indefinitely: Layer 1 has a mature, well-practiced pattern for adding new capabilities (Architecture Freeze → Deterministic Implementation → Runtime Contract Freeze → Runtime Integration → Execution Package Integration → Golden Rebaseline, per ADR-0020 Stage 8 / the pattern ADR-0031 inherits), and that pattern's own momentum is exactly what has crowded out the six unbuilt layers this platform is named for.

## Decision

**Layer 1 (Requirement Intelligence, including every capability redesignated to it as a sub-capability by ADR-0031 D3 — CAP-083 Continuous Improvement, CAP-084 Knowledge Graph, CAP-085 Organizational Memory, CAP-086 Learning Framework) is frozen at its current baseline.** No new Layer 1 capability may be introduced — concretely, **no new CAP number may be allocated in the Layer 1 series** (the blocks `CAP-001…073` and the Layer-1-sub-capability range `CAP-081…086`, per `docs/governance/platform-capability-matrix.md` §3.1) — until this freeze is explicitly lifted (see below).

### Permitted carve-outs

The freeze does **not** prohibit:

1. **Emitting the new inter-layer contract** — implementing `TestableRequirement` / `TestableRequirementSet` as defined by ADR-0034, including whatever Layer 1 code is needed to construct and emit it at the end of a run. This is Layer 1 gaining an *export*, not a new judgement capability.
2. **Integrating the run/stage state model** — wiring Layer 1 into the `run_state.json` state machine defined by ADR-0036. This is orchestration plumbing, not a new capability.
3. **The package renames locked by ADR-0033** — `requirement_intelligence/quality_governance/` → `requirement_intelligence/requirement_quality_governance/` and `requirement_intelligence/execution/` → `requirement_intelligence/execution_package/`. Renames only; no behavior change.
4. **Bugfixes** to any existing Layer 1 capability.
5. **Tests** for any existing Layer 1 capability.

Nothing else. A carve-out that grows into new judgement logic, a new canonical model unrelated to items 1–3, or a new consumed/produced result type is **not** a bugfix and is not covered — it requires the freeze to be lifted first.

### Rationale, stated plainly

Layer 1 has proven, across nine capability arcs (CAP-011 through CAP-086), that this platform can build a governed, deterministic, explainable subsystem well. It has not yet proven it can cross the boundary into Layer 2. Continuing to invest in Layer 1's depth without first proving that crossing is exactly the pattern that produced the current state — a maximally mature single layer and six empty packages — and this ADR exists to stop that pattern from repeating by default.

### How the freeze is lifted

The freeze lifts only by a new, numbered ADR that:

1. Is proposed only after **Layer 2 (Feature Engineering) has reached Runtime Integration** (per the lifecycle ADR-0020 Stage 8 established and ADR-0031 inherits) — i.e., the freeze's exit condition is tied to forward progress on the platform's actual gap, not to a calendar date or a vote alone.
2. Is approved by whatever governance body ratifies ADRs in this repository (Architecture Review Board, per `docs/architecture/architecture-action-register.md` §1's usage of that term) — the same body, not a unilateral decision by a single contributor.
3. States explicitly which new Layer 1 CAP number(s) it authorizes, rather than lifting the freeze in general — the freeze is lifted per-capability, not wholesale, so a future decision to grow Layer 1 again remains a deliberate, visible act rather than a default.

Until such an ADR exists, any pull request or proposal that allocates a new Layer 1 CAP number is out of policy under this ADR.

**Resolution note (additive, 2026-07-25, ADR-0043).** ADR-0043 (Layer 2 Feature Engineering Architecture Freeze) is Layer 2's own Architecture Freeze — stage 1 of the six-stage lifecycle cited above (Architecture Freeze → Deterministic Implementation → Runtime Contract Freeze → **Runtime Integration** → Execution Package Integration → Golden Rebaseline), not stage 4. Precondition 1 above is therefore **not met** by ADR-0043 and **this freeze is not lifted by it** — ADR-0043 says so explicitly (its D8) rather than asserting a precondition that is plainly false against the repository's current state (no Layer 2 code exists). Preconditions 2 and 3 are consequently moot for ADR-0043; it names no Layer 1 CAP number. This freeze remains in full force, unmodified, until a separate, future, numbered ADR satisfies all three preconditions above — proposed only once Layer 2's own implementation (which ADR-0043 does authorize, on its own terms, independent of this freeze — see ADR-0043 D8) reaches Runtime Integration.

## Recommendations (permanent)

1. **No new Layer 1 CAP number without a lifting ADR.** Enforced by review, not by tooling, at this stage.
2. **The five carve-outs are exhaustive.** A sixth kind of permitted change is not inferred by analogy; it requires amending this ADR.
3. **Progress is measured against Layer 2, not against Layer 1.** Any status report citing "platform progress" after this ADR should lead with Layers 2–7's status, not Layer 1's — Layer 1 is understood, from this point forward, as already sufficiently proven.

## Ownership, scope, and governance

- **Owns:** the freeze on new Layer 1 capabilities and its five carve-outs; the lifting procedure.
- **Does not own:** any existing Layer 1 capability's runtime contract (unchanged, owned by ADR-0011–ADR-0030); the Layer 1 → Layer 2 contract itself (ADR-0034); the run/stage state model (ADR-0036); package renames (ADR-0033).
- **Governance:** Accepted, effective immediately. Lifted only per the procedure above.
