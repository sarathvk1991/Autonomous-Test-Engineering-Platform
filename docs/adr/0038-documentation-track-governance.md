# ADR-0038 — Documentation Track Governance

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing (Track B's documents are not numbered ADRs, so there is nothing in the `docs/adr/` sequence to supersede). This ADR **subordinates** Track B's authority rather than superseding a document — see Decision. **Amends:** nothing.
- **Governing design:** none. Evidentiary basis: `docs/architecture/architecture-action-register.md` (ACT-001, the action this ADR closes, re-read in full for this task); `docs/EIOS-REPOSITORY-AUDIT-implementation-baseline.md` (the first repository document to name the Track A/Track B split); `docs/governance/platform-capability-matrix.md:119` and `docs/product/CAP-001-requirements-intelligence.md:1-20` (the two colliding `CAP-001` definitions, re-verified directly for this ADR).
- **Depends on:** ADR-0031 (Authoritative Layer Model — itself an act of choosing one document's authority over a conflicting one, the same pattern this ADR generalizes for documentation tracks).
- **Runtime status:** Not applicable. This is a **documentation governance** decision only — no code, no runtime behavior.

## Problem

Two independent documentation families coexist under `docs/`, re-verified directly for this ADR:

- **Track A** — `docs/adr/`, `docs/architecture/`, `docs/governance/`, `docs/proposals/`, `docs/reviews/`, `docs/releases/` — governs the real, implemented `requirement_intelligence/` code. Its ADRs carry real `Accepted`/`Proposed` status and are cited by, and cite, actual runtime contracts.
- **Track B** — `docs/product/` (14 files: `ADR-001`, `ADR-100`, `ADR-HAP-001`, `CAP-001`, `CAP-100`, `PRA-001`, `PRA-100`, `PRD-001`, `PRD-100`, `PRD-HAP-001`, `RUN-001`, `RUN-100`, `SYS-001`, `SYS-100`, `IMP-100`), `docs/handbook/` (`HB-001`), `docs/standards/` (`STD-000` through `STD-009`) — a separate enterprise-architecture methodology chain. `docs/product/CAP-001-requirements-intelligence.md:12` carries status **"Draft — pending Capability Board approval."**

Both tracks independently assign the identifier `CAP-001` to different things: Track A's `CAP-001` (`docs/governance/platform-capability-matrix.md:119`) is "Connector Framework & Registry"; Track B's `CAP-001` (`docs/product/CAP-001-requirements-intelligence.md:1,10`) is "Requirements Intelligence." This collision is the subject of `docs/architecture/architecture-action-register.md`'s **ACT-001** ("Resolve shared capability identifier collision"), re-confirmed at status **Identified** — named, not yet acted on — with exit criteria: *"A governance action assigns each identifier definition a distinct identifier, **or formally designates one definition as authoritative**, and no repository document retains an unresolved conflicting definition."*

Note: this ADR's Track A / Track B classification covers the architecture-governance document families specifically. Other `docs/` content (`docs/demo/`, `docs/development/`, `docs/operations/`, `docs/user-guide/`, `docs/integrations/`, `docs/productization/`, `docs/audit/`, and the top-level `docs/coding-standards.md`/`docs/naming-conventions.md`) are operational and developer guides, not competing architecture-governance authorities, and are out of this ADR's scope.

## Decision

**Track A is normative.** It governs the real, implemented platform and is the sole authority any future ADR, ticket, or design document defers to for architecture decisions.

**Track B is declared non-normative and frozen.** It is **not deleted** and **not maintained** — its documents remain in the repository as a historical record of a parallel methodology effort, but no future architecture decision cites them as authoritative, and no future contribution is expected to keep them in sync with the real platform.

**Where an identifier collides between the two tracks (`CAP-001` today; any future collision the same way), Track A wins by precedence.** A reader who encounters `CAP-001` anywhere in this repository, without further qualification, is reading Track A's definition ("Connector Framework & Registry"); Track B's competing use of the same identifier is understood, from this ADR forward, to be a document in a frozen, non-normative track, not a live competing claim.

**This closes ACT-001 by precedence, not reconciliation.** No identifier is renumbered, and Track B's fourteen `docs/product/` documents, `HB-001`, and `STD-000`–`STD-009` are not rewritten. `docs/architecture/architecture-action-register.md` is updated (separately, alongside this ADR) to record ACT-001 as **Closed**, citing this ADR as its verification evidence.

## D1 — Why precedence, not renumbering or reconciliation

ACT-001's exit criteria offers two paths: assign distinct identifiers, or formally designate one definition authoritative. Renumbering Track B's `CAP-001` would require rewriting a fourteen-document family (and every internal cross-reference within it) for a track this decision simultaneously declares non-normative and unmaintained — work spent hardening a track this ADR is retiring from architectural authority. Reconciling the two into one merged capability model would require treating Track B's aspirational, Draft-status enterprise-methodology content as equally weighted against Track A's real, implemented, `Accepted`-governed architecture — which they are not, and pretending otherwise would produce a worse document than either track alone. Precedence is the smallest change that satisfies the exit criteria's second, explicitly offered path.

## D2 — Why "not deleted, not maintained" rather than removed

Track B represents real work and a real point of view about how this platform's capabilities could be classified under a different, more formal enterprise-architecture methodology. Deleting it would destroy that record for no governance benefit ACT-001's exit criteria requires — the criteria asks only that no *unresolved conflicting definition* remain, which precedence satisfies without deletion (D3). Declaring it frozen (not maintained) is what prevents it from drifting further out of sync with Track A while continuing to exist as a reference.

## D3 — Why a frozen, still-present Track B document satisfies "no unresolved conflicting definition"

`docs/product/CAP-001-requirements-intelligence.md` still physically exists and still says "Requirements Intelligence" after this ADR — read literally, a conflicting definition of `CAP-001` is still present in the repository. What changes is whether that definition is *unresolved*: before this ADR, a reader had no way to know which of two `CAP-001`s to trust; after it, precedence gives a single, unambiguous, permanent answer, and Track B's document is understood as a frozen historical artifact rather than a live competing claim. The conflict is resolved in the sense the exit criteria requires — no ambiguity about which one governs — without requiring the conflicting text to be erased.

## Recommendations (permanent)

1. **No future ADR, ticket, or design document cites Track B as architectural authority.** Track A alone governs.
2. **No future contribution is required to update Track B for consistency with the real platform.** It is frozen; drift from this point forward is expected and accepted, not a defect to fix.
3. **A future identifier collision (should one arise from work Track A does not yet cover) resolves the same way** — Track A wins by precedence — without requiring a new ADR to restate this rule, unless the collision is *within* Track A itself, which this ADR does not address.
4. **`docs/architecture/architecture-action-register.md` is updated to close ACT-001, citing this ADR, in the same change as this ADR's introduction** — not left to drift out of sync with the decision it records.

## Ownership, scope, and governance

- **Owns:** the normative/non-normative designation of the two documentation tracks, the precedence rule for identifier collisions, and the closure basis for ACT-001.
- **Does not own:** any individual Track A document's own content (unchanged); any individual Track B document's own content (frozen, unchanged, not rewritten); the register's own lifecycle mechanics (`docs/architecture/architecture-action-register.md`, updated alongside this ADR, not redefined by it).
- **Governance:** Accepted, effective immediately. Closes ACT-001 by precedence per D1–D3.
