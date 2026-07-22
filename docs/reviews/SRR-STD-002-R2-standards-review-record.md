# SRR-STD-002-R2 — Standards Review Record

**Capability Contract Standard Proposal · Category: Standards Review Record · Status: Draft · Authority: Standards Review Board (SRB)**

**Reviewing:** `STD-002-R2-PROPOSAL` — *Capability Contract Standard — Proposed Revision to STD-002* (`docs/proposals/capability-contract-standard-std-002-revision-proposal.md`), reviewed exactly as submitted. No content of the proposal is modified by this record — every citation below is to the proposal's own existing text ("Proposal §N"), never a rewrite of it.

**A note on this record's own category.** "Standards Review Record" (`SRR`) is not a formally registered HB-001 document family (HB-001 §20.14 reserves family registration to HB-001 alone) — it is closest in spirit to HB-001 §6.8's own "pre-certification review reports... a review of one candidate capability's readiness, produced before its formal certification is recorded," generalized here from a capability to a Standards proposal. This record does not resolve that classification question; it is noted once, here, rather than left for a future reader to wonder about.

## 1. Executive Summary

The Board reviewed the Proposal in full against HB-001, STD-000 through STD-009, and the existing `CAP-001`/`CAP-100` artifacts it would eventually govern. The Proposal is well-constructed and unusually self-aware — it discloses its own non-authoritative status (Proposal §1.1), self-corrects a Constitutional gap in its own commissioning brief (Proposal §5's restored `Owner`/`Runtime Contract` fields), and proactively names a terminology collision with `CAP-100` §6 rather than leaving it for the Board to discover (Proposal §6.1). **Disclosure is not the same as resolution.** Two defects the Proposal itself names — the terminology collision (Proposal §6.1) and the absence of a concrete migration path for `CAP-001`/`CAP-100` (Proposal §1.2, §13) — remain unresolved in the submitted text and are substantive enough to block adoption as written. **The Board's resolution is Revision Required** (§13, below), not Rejected: the defects are narrow, are within the Proposal's own power to fix, and do not require a wholesale rewrite.

## 2. Review Scope

**In scope:** the Proposal's own eighteen sections (`docs/proposals/...`, §1–§18), evaluated against the twelve Review Criteria (header) and HB-001/STD-000–STD-009. **Out of scope:** re-reviewing `STD-002` v1.0 itself (unmodified by the Proposal, and not up for review here); independently re-assessing `CAP-001` or `CAP-100` on their own merits (they are cited only insofar as the Proposal's own claims about them are checked for accuracy).

## 3. Strengths

- **Explicit, repeated honesty about its own governance status** (Proposal §1.1, §13, §18) — the Proposal never allows its own thoroughness to imply authority it has not received.
- **Self-correcting against a Constitutional gap in its own commissioning brief** — Proposal §5 restores `Owner` and `Runtime Contract`, both required by STD-000 Rule 2 and Principle 9, neither present in the Proposal's own literal source brief.
- **Proactive disclosure of its own terminology collision** (Proposal §6.1) rather than an omission the Board would have had to find independently.
- **Clean separation maintained across every adjacent Engineering Artifact family** (Proposal §7–§11) — each restates, and does not redefine, ADR, RUN, SYS, PRA, and IMP's own existing authority.
- **No retroactive change asserted over `CAP-001` or `CAP-100`** (Proposal §1.2) — the Proposal is explicit that adoption would govern future Capability Models only.
- **Correct self-classification of the governance action required** — the Proposal identifies its own change as Architectural-category (STD-006 §7) and lays out a concrete, staged adoption path (Proposal §13), rather than assuming a lighter review would suffice.

## 4. Issues Identified

Distinguishing observation from finding, per this record's own Writing Style:

| ID | Criterion | Finding |
| --- | --- | --- |
| **ISSUE-1** | Terminology / Standards Consistency | Proposal §6's own "Capability Maturity Model" (`Declared → Architected → Implemented → Operational`) shares its exact name with `CAP-100` §6's already-published Capability Maturity Model (`Conceptual → Piloted → Adopted → Standardized`), which measures a different axis entirely. The Proposal names this collision (§6.1) but does not resolve it. |
| **ISSUE-2** | Migration | No concrete migration or grandfathering path exists for `CAP-001`/`CAP-100`. Proposal §13's own adoption-path table lists the transition path as "Future governance act, not this document" — an acknowledgment of the need, not a plan. |
| **ISSUE-3** | Standards Consistency | A second, independent compression of STD-002 §3's own eight-stage Capability Lifecycle now exists (the Proposal's own four-level model, alongside `CAP-100` §5's own, already-published five-stage compression), with different collapse boundaries. Proposal §6.1 names this as "future work," unresolved. |
| **ISSUE-4** (minor) | Capability Contract completeness | Proposal §5's restored `Runtime Contract` field cites STD-000 Rule 2 as its own justification for existing, but does not cite STD-003 §4's own canonical Runtime Contract elements to specify what the field's own content should actually contain. |
| **ISSUE-5** (minor, not attributable to the Proposal) | Identifier / Family registration | Neither this record's own `SRR` category nor the Proposal's own working identifier (`STD-002-R2-PROPOSAL`) is a formally registered HB-001 family or identifier scheme (HB-001 §20.14). The Proposal itself already flags its own identifier as non-canonical (Proposal §1.1); this is noted for completeness, not as a defect of the Proposal's own making. |

## 5. Required Revisions

**Each is within the Proposal's own scope to resolve; none requires amending `CAP-100` or `CAP-001` directly, which would exceed this review's own authority.**

1. **Rename Proposal §6's own model** to a name that does not collide with `CAP-100` §6 (e.g. "Capability Development Stage" or "Capability Realization Level") — resolving ISSUE-1 without requiring `CAP-100` to change.
2. **Add a concrete migration provision to Proposal §13**: at minimum, a grandfather clause stating `CAP-001` and `CAP-100` remain valid indefinitely under `STD-002` v1.0's own schema unless and until each undergoes its own next Architectural-category revision (STD-006 §7), at which point the Proposal's own revised schema (§5) would apply — resolving ISSUE-2 without forcing an immediate, disruptive rewrite of either existing Artifact.
3. **Explicitly reconcile Proposal §6's own compression against `CAP-100` §5's own compression** — either declaring the Proposal's own (renamed, per Revision 1) model the sole canonical compression going forward, with `CAP-100` §5 flagged for its own future harmonization, or demonstrating the two are compatible refinements at different grain, consistent with the precedent this platform's own document series already sets for reconciling similar terminology gaps (e.g. STD-007 §5.1) — resolving ISSUE-3.

## 6. Optional Improvements

1. Cite STD-003 §4's own canonical Runtime Contract elements explicitly within Proposal §5's `Runtime Contract` field description (addresses ISSUE-4; does not block adoption).
2. If the Standards Review Board intends to carry the working identifier `STD-002-R2` through to adoption, consider whether that identifier itself should be formally registered under HB-001 §20.14 at the same time, rather than left permanently informal (addresses ISSUE-5; does not block adoption).

## 7. Governance Assessment

**PASS.** The Proposal remains within the authority granted to a Design-Proposal-class document (HB-001 §6.3 analogy, Proposal §1.1) — it does not assert authority it has not received, and it correctly identifies the STD-006 §6/§7 approval chain required before adoption (Proposal §13). No governance overreach found.

## 8. Constitutional Assessment

**PASS.** No violation of HB-001 or STD-000 identified. The Proposal's own restoration of `Owner` and `Runtime Contract` (Proposal §5) is evidence of active conformance-checking against STD-000 Rule 2 and Principle 9, not a violation of either. The Proposal's own explicit refusal to formally register a new HB-001 family (Proposal §1.1) is likewise correct restraint, not a gap.

## 9. Standards Assessment

**FAIL, pending Required Revisions 1 and 3 (§5).** Two contradictions were identified against `CAP-100` (an existing Artifact built under `STD-002`'s own authority, not a Standard's own text directly): the Capability Maturity Model naming collision (ISSUE-1) and the lifecycle-compression proliferation (ISSUE-3). No contradiction against `STD-000`, `STD-004`, `STD-005`, `STD-006`, or `STD-007` was found — every citation to those Standards in the Proposal (§4, §7–§11, §13) was checked and found to reference, not restate or contradict, its source.

## 10. Migration Assessment

**FAIL, pending Required Revision 2 (§5).** No concrete migration path exists in the submitted Proposal — Proposal §13 correctly identifies that one is needed but defers it entirely to an unspecified "future governance act." A Standard this Board adopts SHALL have a stated position on its own existing artifacts' continuity before adoption, not after.

## 11. Risk Assessment

The Board reviewed Proposal §15's own five named risks (Premature authority assumption, Naming collision persistence, Compression proliferation, Retrofit ambiguity) and confirms each is accurately characterized. **The Board adds one risk of its own:** approving a proposal that already discloses two unresolved defects (ISSUE-1, ISSUE-2) without requiring their resolution first would establish a precedent that self-disclosure substitutes for correction — directly undermining STD-008 §4's own Evidence Before Assertion principle, platform-wide, for every future proposal reviewed under this same process. This risk is the Board's own primary reason for declining to approve the Proposal as submitted, even Conditionally.

## 12. Final Recommendation

**Revision Required, not Rejected.** The Proposal's fundamentals — the Capability Contract schema (Proposal §5), the relationship definitions to ADR/RUN/SYS/PRA/IMP (Proposal §7–§11), and its own accurate self-assessment of the governance action required (Proposal §13) — are sound. The three Required Revisions (§5, above) are narrow, well-scoped, and resolvable without a wholesale rewrite of the Proposal.

## 13. Formal Resolution

**REVISION REQUIRED.**

- **Required Revisions** (binding, must all be addressed before resubmission): 1. Rename the colliding maturity model (§5.1, above). 2. Add a concrete migration/grandfathering provision (§5.2). 3. Reconcile the lifecycle-compression proliferation against `CAP-100` §5 (§5.3).
- **Optional Improvements** (non-binding): 1–2, above (§6).
- **Resubmission.** The Engineering Methodology Council SHALL resubmit a revised proposal addressing all three Required Revisions before the Board reconsiders the Standards Assessment (§9) and Migration Assessment (§10) findings above; the Governance Assessment (§7) and Constitutional Assessment (§8) findings, both PASS, remain valid for the resubmission unless the revision itself introduces a new governance or constitutional question.
- **This record's own disposition.** This record is Frozen upon adoption of this Formal Resolution (HB-001 §8), permanent per HB-001 §9, and is never reopened for this same review cycle — a resubmission produces a **new** Standards Review Record, restating STD-007 §9's own Non-Silent Supersession discipline, applied here to review records specifically, never an edit to this one.

---

*End of SRR-STD-002-R2, Draft.*
