# Decision Review Package — ACT-001

Prepared for the Architecture Review Board. This package supports deliberation only. It does not constitute an architecture assessment, an implementation plan, or a governance decision.

---

## 1. Executive Summary

ACT-001, "Resolve shared capability identifier collision," was approved by the Architecture Review Board to close a Governance Debt item identified in the Repository Architecture Assessment Report (RAAR-001): the identifier `CAP-001` is independently assigned to two unrelated capabilities, "Connector Framework & Registry" in the platform capability matrix and "Requirements Intelligence" in the Engineering Intelligence Operating System (EIOS) target-architecture lineage.

Implementation of the approved resolution began under the ACT-001 Architecture Action Execution Record, which directed that the "Connector Framework & Registry" identifier be reassigned within its existing domain block. Execution was paused before any repository file was modified. The Implementation Engineer identified that `docs/governance/platform-capability-matrix.md` states, in two separate sections, that assigned capability identifiers are immutable and may never be renumbered. This directly conflicts with the approved resolution's central step.

This conflict was not identified during preparation of the Execution Record and requires a governance decision by the Architecture Review Board before implementation of ACT-001 can resume.

---

## 2. Background

**Original finding (RAAR-001).** The assessment identified a shared identifier naming two unrelated capabilities as a Governance Debt item of High priority (RAAR-001 §11), and as a contributing factor to the Architecture Consistency rating of 2 out of 5 (RAAR-001 §7). The assessment's recommended action, carried into the roadmap as the first sequenced step, was to resolve the collision through a targeted governance action before any further document references either definition (RAAR-001 §13, §14, Step 1).

**Approved action (Architecture Action Register).** ACT-001 was registered with Priority High, Category Governance, and the following Exit Criteria: "A governance action assigns each identifier definition a distinct identifier, or formally designates one definition as authoritative, and no repository document retains an unresolved conflicting definition." The Exit Criteria, as recorded, admit either of two resolution forms: assigning distinct identifiers, or designating one definition authoritative without renumbering.

**Approved implementation approach (ACT-001 Execution Record).** The Execution Record's proposed resolution (Section 6) directed that the Track B definition, "Requirements Intelligence," remain unchanged, on the basis that it is grandfathered under `HB-001` §20.4 and cited by thirteen further documents. It directed that the Track A definition, "Connector Framework & Registry," be reassigned to the next available identifier within its own domain block, on the stated basis that the capability has no recorded Freeze Date in the Architecture Freeze Index and therefore "remains eligible for identifier reassignment."

---

## 3. Execution Finding

Execution proceeded through Steps 1 and 2 of the approved Implementation Plan without incident: the resolution direction was treated as confirmed, and the retained Track B definition was confirmed to require no change.

Execution stopped at Step 3, "Locate the definition to be reassigned... and identify the next available identifier." Direct inspection of `docs/governance/platform-capability-matrix.md`, the document the approved plan directed be edited at this step, surfaced the following text, not identified during the Execution Record's Current State Analysis:

- Section 3.1: "Capability IDs are immutable and sequential... An ID, once assigned, is permanent. A renamed capability keeps its ID; a removed capability's ID is retired, never reused."
- Section 8, Step 1: "Never reuse a retired ID and never renumber an existing one."

No further step of the Implementation Plan was attempted. Steps 4 through 8 each depend on Step 3 producing a valid reassigned identifier for the Track A definition.

---

## 4. Governance Conflict

**The governing rule discovered during execution.** `docs/governance/platform-capability-matrix.md`, the document that defines the Track A "Connector Framework & Registry" capability, states in two places that a capability identifier, once assigned, is permanent and may never be renumbered.

**The implementation assumption that conflicts with it.** The approved resolution (ACT-001 Execution Record, Section 6) assumed the Track A identifier was available for reassignment because the capability holds no recorded Freeze Date in the Architecture Freeze Index. The Freeze Date and the identifier-permanence rule are separate governance mechanisms in the same document family: Freeze Date governs whether a capability's architectural contract may still evolve; the identifier-permanence rule governs whether the capability's ID may change. The absence of a recorded Freeze Date has no bearing on the identifier-permanence rule, which applies independent of freeze status.

**Why both cannot simultaneously be satisfied.** The approved resolution requires reassigning the Track A identifier. The governing document that identifier belongs to states, without qualification, that an assigned identifier is permanent and may never be renumbered. Executing the approved resolution as written would satisfy the ACT-001 Exit Criteria while directly violating an explicit rule in the same document being edited to satisfy it. The two cannot both be true of the same action without either an explicit exception to the identifier-permanence rule or a change in which definition is reassigned, or without reassigning neither.

---

## 5. Decision Options

Three options are supported by the evidence in the ACT-001 Architecture Action Execution Report. Each is presented neutrally.

### Option 1

**Description.** Grant a one-time, explicitly recorded exception to the identifier-permanence rule (`platform-capability-matrix.md` §3.1, §8) and proceed with the resolution as originally approved: reassign the Track A "Connector Framework & Registry" identifier within its existing domain block.

**Advantages.** Resumes the Implementation Plan already prepared in the ACT-001 Execution Record without redrafting it. Confined to the smallest citation footprint identified in the Execution Record: two governance documents (the capability matrix and its mirrored coverage dashboard) plus one release note.

**Risks.** Establishes a recorded precedent that an identifier described elsewhere in the same document as "permanent" can be reassigned given sufficient justification, which could be cited in support of reopening other identifiers the matrix currently treats as fixed.

**Repository Impact.** Low in scope: `docs/governance/platform-capability-matrix.md`, `docs/governance/architecture-coverage-dashboard.md`, and `docs/releases/v1.1.0-requirement-intelligence.md`.

**Governance Impact.** Requires a formally recorded exception to an explicit rule in `platform-capability-matrix.md` §3.1 and §8. The rule itself is not amended; a single instance is excepted from it.

**Additional Work Required.** Drafting and recording the exception; resuming Steps 3 through 8 of the existing Implementation Plan.

### Option 2

**Description.** Reassign the Track B "Requirements Intelligence" identifier instead, leaving the Track A "Connector Framework & Registry" identifier and the identifier-permanence rule undisturbed.

**Advantages.** Does not conflict with `platform-capability-matrix.md` §3.1 or §8, since that rule governs Track A's own capability register and does not apply to the Track B document.

**Risks.** `HB-001` §20.4 records a grandfather clause preserving the Track B "-001" series, including `CAP-001`, from renumbering under the platform's own later Bounded Context Classification scheme. While that clause does not explicitly prohibit renumbering for the purpose of resolving this collision, its evident intent, as recorded in `HB-001`, is preservation of the existing "-001" series identifiers. Renumbering under this option runs counter to that recorded intent.

**Repository Impact.** High in scope: the Execution Record identifies thirteen product, architecture, and standards documents that cite the Track B `CAP-001` definition (ACT-001 Execution Record, Section 3), each requiring review for a required update.

**Governance Impact.** Includes documents within the completed `STD-002` governance-lifecycle review record set (`SRR-STD-002-R2`, `SRR-STD-002-R3`, `DRC-STD-002-R2`, `BLR-STD-002-V2.0`), which RAAR-001 identifies as the repository's one complete, dated governance lifecycle exercise. Amending historical review records of a closed governance cycle is not addressed by any of the four input documents.

**Additional Work Required.** A substantially larger review and update effort than Option 1, spanning thirteen documents, plus a determination of how the historical `STD-002` review records should be treated.

### Option 3

**Description.** Resolve the collision through a governance action that formally designates one definition as authoritative for citation purposes, without reassigning either capability's identifier. This satisfies the second disjunct of the ACT-001 Exit Criteria directly: "formally designates one definition as authoritative."

**Advantages.** Does not conflict with `platform-capability-matrix.md` §3.1 or §8, since no identifier is reassigned. Does not require reviewing or amending the thirteen documents identified under Option 2, since the Track B document's identifier and content are unchanged. Matches the Impact Assessment already recorded in the ACT-001 Execution Record (Section 5), which separately identified that `HB-001` §20.4 could receive a supplementary note disclosing that its grandfather clause addresses only the Track B series and does not resolve the Track A definition.

**Risks.** The specific mechanism for "designating one definition as authoritative" is not detailed in any of the four input documents and would need to be defined by the Board. Both instances of the literal string `CAP-001` remain present in the repository under this option; any future process that assumes one identifier resolves to exactly one capability, repository-wide rather than within a track, would still require scope-awareness.

**Repository Impact.** Low to Medium: no change to `platform-capability-matrix.md`'s or `CAP-001-requirements-intelligence.md`'s substantive content; addition of a new governance record and, per the Execution Record's own Impact Assessment, an optional supplementary note in `HB-001` §20.4.

**Governance Impact.** Requires drafting new governance-record language sufficient to satisfy the "formally designates" language of the Exit Criteria without amending either capability's own defining document.

**Additional Work Required.** Drafting the designation record; determining, with the Board, its required content and form.

---

## 6. Comparative Analysis

| Criterion | Option 1 (except and reassign Track A) | Option 2 (reassign Track B) | Option 3 (designate authoritative, no reassignment) |
|---|---|---|---|
| Governance compliance | Conditional on a recorded exception to an explicit rule | Compliant with Track A's rule; in tension with `HB-001` §20.4's recorded preservation intent | Compliant with both; no rule directly addresses this mechanism |
| Repository impact | Low (three documents) | High (thirteen-plus documents) | Low to Medium (no defining document changed; one new record) |
| Documentation impact | Low | High, including historical `STD-002` review records | Low |
| Implementation effort | Low; resumes the existing Implementation Plan | High; requires a new review and update sequence | Low to Medium; requires new record language |
| Long-term maintainability | Introduces a precedent for excepting "permanent" identifiers | Preserves Track A's permanence principle intact | Preserves both existing identifiers; leaves shared string present, scope-qualified |
| Traceability | High; narrow footprint already mapped in the Execution Record | Uncertain; depends on treatment of historical review records | Medium; depends on the Board defining the designation mechanism |

---

## 7. Questions for the Architecture Review Board

- Should identifier immutability, as stated in `platform-capability-matrix.md` §3.1 and §8, be treated as absolute, with no exception available under any circumstance?
- Is a one-time governance exception to that rule acceptable for the purpose of resolving this collision, if Option 1 is preferred?
- If Option 2 is selected, should the historical `STD-002` review records (`SRR-STD-002-R2`, `SRR-STD-002-R3`, `DRC-STD-002-R2`, `BLR-STD-002-V2.0`) be amended, formally superseded, or left unchanged with a forward-referencing annotation?
- Does the Exit Criteria's second disjunct, "formally designates one definition as authoritative," admit a resolution that leaves both instances of the identifier string present in the repository, as Option 3 would produce?
- Should `HB-001` §20.4 be supplemented, as the Execution Record's Impact Assessment already contemplated, to disclose that its grandfather clause does not address the Track A definition, regardless of which option is selected?

---

## 8. Recommendation

Of the three options presented, Option 3 is recommended.

This recommendation rests on evidence already contained in the four input documents. First, the ACT-001 Exit Criteria, as recorded in the Architecture Action Register and reproduced in the Execution Record, explicitly admits resolution by designating one definition authoritative, without requiring that any identifier be reassigned; Option 3 satisfies this disjunct directly. Second, Option 3 is the only option that avoids both governance conflicts identified in this package: it does not require an exception to the identifier-permanence rule discovered in `platform-capability-matrix.md` (the conflict blocking Option 1), and it does not require reviewing or amending the thirteen-document footprint, including closed `STD-002` governance-lifecycle review records, associated with Option 2. Third, Option 3 aligns with a mitigation the Execution Record itself already identified in its Impact Assessment (Section 5): a supplementary note in `HB-001` §20.4 disclosing the scope gap in its existing grandfather clause, without amending any defining document's substantive content.

This recommendation does not resolve the open question of what specific mechanism should constitute the "formal designation" required to close ACT-001 under Option 3. That determination remains for the Board.

---

## 9. Required Board Decision

**Decision:**

**Approved Option:**

**Conditions:**

**Follow-up Actions:**

**Effective Date:**

**Decision Authority:**

**Review Required:**

---

## 10. Effect on Existing Governance Documents

**Repository Architecture Assessment Report (RAAR-001).** Remains valid without amendment. The underlying finding, that the repository contains a shared capability identifier naming two unrelated capabilities, is unaffected by which resolution option the Board selects. No option presented in this package alters the facts RAAR-001 recorded.

**Architecture Action Register.** Requires amendment. ACT-001's recorded status and supporting notes must be updated to reflect that execution was paused pending this Board decision, consistent with the recommendation already made in the ACT-001 Execution Report. Once the Board decides, the register entry should record which disjunct of the Exit Criteria the selected option satisfies.

**ACT-001 Architecture Action Execution Record.** The ACT-001 Architecture Action Execution Record remains the historical record of the originally approved implementation approach. Following the Board's decision, it should either be revised to reflect the approved implementation approach or formally superseded by a new revision. The original version should be retained as part of the governance history.

---

## 11. Next Steps

```
Board Decision
    ↓
Update ACT-001 Execution Record (Section 6 and dependent sections revised per the Board's selected option)
    ↓
Resume Implementation
    ↓
Verification
    ↓
Update Architecture Action Register
    ↓
Close ACT-001
```

This workflow is scoped to ACT-001 only. It does not extend to any other action recorded in the Architecture Action Register.
