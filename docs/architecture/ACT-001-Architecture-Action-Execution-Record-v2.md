# Architecture Action Execution Record — ACT-001 — Version 2.0

Status: Execution package prepared for Architecture Review Board review, superseding the implementation approach in Version 1.0 following the Board's decision recorded in the ACT-001 Architecture Review Board Decision Record (ARB-DEC-001). This is a temporary execution document that exists only while ACT-001 is active in the Architecture Action Register. It is superseded by the Verification Evidence recorded against ACT-001 once the action is Closed.

**Relationship to Version 1.0.** Version 1.0 proposed resolving ACT-001 by reassigning the Track A "Connector Framework & Registry" identifier. Execution of that plan was paused at Step 3 when `docs/governance/platform-capability-matrix.md` was found to state, in two places, that assigned capability identifiers are immutable and may never be renumbered. The Architecture Review Board resolved this conflict by adopting Decision Option 3 in ARB-DEC-001: formally designate the Track B "Requirements Intelligence" definition as authoritative for citation, reassign no identifier, and grant no exception to the identifier-permanence rule. This Version 2.0 revises the sections of the Execution Record affected by that decision. Version 1.0 is retained in full, unmodified, as part of governance history; it is not deleted or overwritten.

**Note on repository organization.** A separate proposal exists for a broader repository governance information architecture and migration of governance artifacts into a reorganized directory structure. That proposal is explicitly out of scope for ACT-001 and is not assumed, referenced as authority, or acted upon by this Execution Record. This Execution Record addresses only the ACT-001 identifier-collision action under the Board's Option 3 decision.

---

## Version 2.0 Change Summary

Every section below is labeled with its status relative to Version 1.0: **UNCHANGED**, **UPDATED**, **REPLACED**, or **REMOVED**. Only sections affected by the Board's decision or by information discovered during Version 1.0 execution are revised. A full comparison appears in Appendix A.

---

## 1. Action Summary

**Status relative to Version 1.0: UPDATED**

| Field | Value |
|---|---|
| Action ID | ACT-001 |
| Title | Resolve shared capability identifier collision |
| Priority | High |
| Current Status | Identified (per Architecture Action Register; resumption of execution has been authorized by ARB-DEC-001, pending the Register update recorded as a follow-up action in that decision) |
| Source Assessment References | RAAR-001 §4 Repository Identity; §10 Repository Risks (Architectural); §11 Architectural Debt (Governance Debt, High); §13 Prioritized Recommendations, Immediate; §14 Recommended Roadmap, Step 1 |
| Exit Criteria | A governance action assigns each identifier definition a distinct identifier, or formally designates one definition as authoritative, and no repository document retains an unresolved conflicting definition. |
| Approved Implementation Direction | Decision Option 3, adopted in the ACT-001 Architecture Review Board Decision Record (ARB-DEC-001): formal designation of the Track B "Requirements Intelligence" definition as authoritative, without identifier reassignment. |
| Supersedes | ACT-001 Architecture Action Execution Record, Version 1.0 (retained as governance history). |

This summary is reproduced from the Architecture Action Register and updated only to record the Board's decision and this document's version relationship. The Register itself has not yet been amended; that amendment is a follow-up action rather than an effect of this document.

---

## 2. Objective

**Status relative to Version 1.0: UPDATED**

This action exists because the repository's capability identifier `CAP-001` is assigned, independently, to two unrelated capabilities: "Connector Framework & Registry" (Track A), a real, implemented capability governed by the platform capability matrix, and "Requirements Intelligence" (Track B), a capability document within the Engineering Intelligence Operating System (EIOS) target-architecture lineage. This remains the Governance Debt item RAAR-001 identifies, unchanged by the Board's decision.

Under Version 1.0, successful completion was defined as the string `CAP-001` resolving, without qualification, to exactly one capability, achieved by reassigning the Track A identifier. Execution of that approach was blocked by the identifier-permanence rule in `platform-capability-matrix.md` §3.1 and §8, and the Board did not adopt it.

Under this Version 2.0, successful completion is defined as: a governance record exists that formally designates the Track B "Requirements Intelligence" definition as authoritative for repository citation purposes; neither capability's identifier is renumbered or reassigned; the identifier-permanence rule remains intact and unexcepted; and both instances of the identifier string `CAP-001` remain present in the repository, each resolvable within its own track through the designation record rather than through a repository-wide rename. This satisfies the Exit Criteria's second disjunct — "formally designates one definition as authoritative" — directly, consistent with ARB-DEC-001 §3.

---

## 3. Repository Scope

**Status relative to Version 1.0: UPDATED**

The following repository areas are within scope for this action under the Board's Option 3 decision. Where scope has narrowed relative to Version 1.0, the change is noted.

**Governance documents.**

- `docs/governance/platform-capability-matrix.md` — the defining source of the Track A `CAP-001`, section 5.1. **No substantive content change required** under Option 3; the identifier is not reassigned. (Version 1.0 required editing this document's identifier and domain-block range table; that requirement is withdrawn.)
- `docs/governance/architecture-coverage-dashboard.md` — mirrors the Track A `CAP-001` row. **No change required**, for the same reason. (Version 1.0 required a mirrored edit; withdrawn.)
- A new governance designation record, to be authored, formally naming the Track B definition as authoritative for citation. This record is the primary new artifact this action produces. (New requirement introduced by Option 3.)

**Product and architecture documents (Track B lineage).**

- `docs/product/CAP-001-requirements-intelligence.md` and the thirteen further product, architecture, and standards-lifecycle documents identified in Version 1.0 Section 3 continue to require **no content change**, consistent with Version 1.0's own analysis, which is unaffected by the choice between Version 1.0's and this document's implementation approach.

**Standards and governance-lifecycle documents.**

- `docs/handbook/HB-001-platform-engineering-handbook.md` §20.4 — its grandfather clause remains unchanged. A supplementary note disclosing that the clause addresses only the Track B `-001` series, and does not extend to or resolve the Track A definition, **remains an option available to whoever authors the designation record**, consistent with the mitigation the Decision Review Package identified. It is not mandated by the Exit Criteria and is not required for this action to reach Verified status.
- `docs/standards/STD-006-engineering-governance-standard.md`, `docs/standards/STD-009-engineering-adoption-standard.md`, and the `STD-002` proposal and review-record family: **no change required**, unchanged from Version 1.0's analysis.

**Release documentation.**

- `docs/releases/v1.1.0-requirement-intelligence.md` — cites the Track A `CAP-001` in connection with `CONNECTOR_REGISTRY_VERSION`. **No change required.** Version 1.0 required updating this citation only if the Track A identifier were reassigned; since it is not, the existing citation remains accurate as written.

**Diagrams, source code, assessment record.** Unchanged from Version 1.0: no diagrams exist outside inline Markdown structure; no source or test file references the literal identifier `CAP-001`; the Repository Audit remains a point-in-time record not modified by this action.

---

## 4. Current State Analysis

**Status relative to Version 1.0: UPDATED**

The current-state findings recorded in Version 1.0 remain accurate and are carried forward without change: the identifier `CAP-001` is assigned to two capability definitions that do not reference one another (Section 4, Version 1.0); no governance record designates either definition authoritative over the other; the definitions are not duplicated in content, only in identifier.

One fact is now settled rather than open: the identifier-permanence rule in `platform-capability-matrix.md` §3.1 and §8 — discovered during Version 1.0 execution and analyzed in the ACT-001 Decision Review Package — is confirmed governing and unexcepted. ARB-DEC-001 §3 records that no exception to this rule is granted. This Version 2.0 treats that rule as a fixed constraint on the resolution rather than as an open question requiring further Board input.

---

## 5. Impact Assessment

**Status relative to Version 1.0: REPLACED**

| Document family | Required modification | Reason | Architectural impact | Downstream impact |
|---|---|---|---|---|
| Governance (capability matrix, coverage dashboard) | None to substantive content. | Option 3 does not reassign either capability's identifier; the identifier-permanence rule is preserved intact. | None. The Track A capability's identifier, maturity rating, and domain-block position are undisturbed. | None. |
| New governance designation record | Author and adopt a record formally designating the Track B "Requirements Intelligence" definition as authoritative for citation purposes. | Directly satisfies the Exit Criteria's "formally designates one definition as authoritative" disjunct, per ARB-DEC-001 §3–§4. | Low. Introduces one new governance record; amends no existing defining document. | Establishes the citation reference future documents should use when disambiguation is required. |
| Product and CAP-001-lineage documents (Track B) | None to their defining content. | Consistent with Version 1.0's own Impact Assessment, unaffected by the choice of implementation approach. | None. | None. |
| Standards and governance-lifecycle documents (`HB-001` §20.4 and others) | Optional: a supplementary note in `HB-001` §20.4 disclosing that its grandfather clause addresses only the Track B series. | Closes an implicit gap without amending any defining document's substantive content, per the mitigation identified in the Execution Record's own Version 1.0 Impact Assessment and referenced in ARB-DEC-001 §4. | Low; editorial addition, optional. | None. |
| Release documentation | None. | The Track A identifier is not reassigned, so the existing historical citation remains accurate as written. | None. | None. |
| Repository Audit | None. | Unchanged from Version 1.0: retroactive editing would misrepresent the evidence base the assessment relied on. | None. | None. |
| Source code | None. | Unchanged from Version 1.0: no source or test file references the literal identifier `CAP-001`. | None. | None. |

**Repository Changes Summary.** Relative to Version 1.0, the net repository footprint of this action is substantially reduced: no existing governance, product, standards, or release document requires a substantive edit. The action's sole required change is the creation of one new governance designation record, with an optional editorial note in `HB-001` §20.4.

---

## 6. Recommended Implementation Approach

**Status relative to Version 1.0: REPLACED**

This section records the Board-confirmed resolution, per ARB-DEC-001, superseding the resolution originally proposed in Version 1.0 Section 6.

**Identifier that remains authoritative.** `CAP-001` — Requirements Intelligence (the Track B definition). This is unchanged from Version 1.0: `HB-001` §20.4 grandfathers this identifier as part of the platform's founding `-001` series, and thirteen further documents cite it as precedent or dependency.

**Identifier that changes.** None. Version 1.0 proposed reassigning the Track A "Connector Framework & Registry" identifier. The Board did not adopt this; `platform-capability-matrix.md` §3.1 and §8 state that an assigned identifier is permanent and may never be renumbered, and ARB-DEC-001 grants no exception to that rule.

**Mechanism of resolution.** A new governance designation record shall be authored, formally stating that, for repository citation purposes where disambiguation between the two `CAP-001` definitions is required, the Track B "Requirements Intelligence" definition is authoritative. This record does not amend `platform-capability-matrix.md`, `architecture-coverage-dashboard.md`, or `CAP-001-requirements-intelligence.md`. Both instances of the identifier string `CAP-001` remain in the repository, each valid and unambiguous within the scope of its own track; the designation record resolves cross-track citation ambiguity without altering either track's identifier.

**Required repository updates.** None to existing governance, product, or release documents. One new governance designation record is created.

**Reference updates.** None required, since the Track A identifier is not reassigned.

**Validation activities.**

- Perform a repository-wide search for the string `CAP-001` after the designation record is adopted, and confirm that every occurrence remains attributable to a specific, identifiable track (Track A or Track B) through its surrounding document context, with no document asserting the two definitions as identical or interchangeable.
- Confirm the Track B `CAP-001` lineage (the thirteen documents identified in Version 1.0 Section 3) requires no content change, consistent with Section 3 above.

---

## 7. Implementation Plan

**Status relative to Version 1.0: REPLACED**

**Step 1.** Record that the Architecture Review Board has confirmed the resolution direction as Decision Option 3, per ARB-DEC-001, superseding the direction proposed in Version 1.0. *(Complete: recorded in ARB-DEC-001 §3.)*

**Step 2.** Confirm that the Track B definition (`docs/product/CAP-001-requirements-intelligence.md`) and its citing lineage require no content change. *(Complete: confirmed under Version 1.0 Step 2 and reconfirmed under Section 3 above; unaffected by the change in approach.)*

**Step 3.** Confirm that the Track A definition (`docs/governance/platform-capability-matrix.md` §5.1) and its mirrored dashboard entry require no content change, and that no identifier reassignment is to be performed. *(Replaces Version 1.0 Step 3, which directed locating a new identifier for reassignment.)*

**Step 4.** Draft the governance designation record required by Section 6 above, formally designating the Track B "Requirements Intelligence" definition as authoritative for citation purposes.

**Step 5.** Determine, at the discretion of whoever authors the designation record, whether to include the optional supplementary note in `HB-001` §20.4 identified in Section 5 above. If included, draft and add the note without amending the substantive content of `HB-001`'s grandfather clause.

**Step 6.** Perform the repository-wide search for `CAP-001` specified in Section 6's Validation Activities, and confirm every remaining reference is attributable to a specific track.

**Step 7.** Submit the designation record, the search evidence, and (if prepared) the `HB-001` note to the Architecture Review Board as Verification Evidence against the ACT-001 Exit Criteria.

---

## 8. Validation Checklist

**Status relative to Version 1.0: REPLACED**

- [ ] Resolution direction confirmed as Decision Option 3 by the Architecture Review Board (ARB-DEC-001).
- [ ] Platform capability matrix and architecture coverage dashboard confirmed unchanged in substantive content.
- [ ] Governance designation record drafted, formally naming the Track B definition authoritative for citation.
- [ ] `HB-001` §20.4 supplementary note added, or its omission explicitly recorded as a discretionary choice.
- [ ] Repository-wide search confirms every `CAP-001` reference remains attributable to a specific track.
- [ ] Track B `CAP-001` lineage confirmed unchanged.
- [ ] No repository document reassigns or renumbers either capability's identifier.
- [ ] Designation record submitted to the Architecture Review Board and available as Verification Evidence.

---

## 9. Risks and Dependencies

**Status relative to Version 1.0: REPLACED**

| Risk | Impact | Mitigation |
|---|---|---|
| The designation record's required form or content is under-specified. | The Decision Review Package and ARB-DEC-001 both identify that the specific mechanism for "formal designation" is not detailed in any input document and remains for definition during this action's execution. | Define the designation record's content and form as part of Step 4, and submit it for Board confirmation before treating it as satisfying the Exit Criteria. |
| Both instances of `CAP-001` remaining present could still mislead a future process that assumes repository-wide identifier uniqueness. | ARB-DEC-001 §4 and the Decision Review Package identify this as a residual risk of Option 3 itself, not of this action's execution. | Ensure the designation record states explicitly that it resolves cross-track citation ambiguity rather than asserting that only one `CAP-001` instance exists repository-wide. |
| A future, separate revision to the Track B `CAP-001` document (contemplated in the `STD-002` capability-contract-standard proposals) could be scheduled concurrently with this action. | Concurrent changes to the same document could conflict, though this action itself makes no change to that document. | Confirm, before treating Step 2 as closed, whether such a revision is active; if so, no dependency exists for this action's own steps, but coordination is advisable to avoid confusing citation records. |
| The repository governance information architecture proposal, if it later becomes an approved action, could relocate the designation record or the Execution Record itself. | A future reorganization action, separate from ACT-001, is under proposal review and is explicitly not authorized under this action. | This Execution Record makes no assumption about future file locations; it depends only on documents at their current, present paths. |

**Dependencies.** This action depends only on ARB-DEC-001 (already recorded) and on no other in-progress governance action. It has no dependency on the repository governance information architecture proposal referenced in the header note; that proposal, if and when approved, would be a separate action with its own Execution Record.

---

## 10. Evidence Required

**Status relative to Version 1.0: REPLACED**

The following evidence must be available before this action can progress through the lifecycle stages described in Section 12.

- The governance designation record, showing the formal designation of the Track B "Requirements Intelligence" definition as authoritative for citation.
- Confirmation that `docs/governance/platform-capability-matrix.md` and `docs/governance/architecture-coverage-dashboard.md` remain unchanged in substantive content.
- The `HB-001` §20.4 supplementary note, if prepared, or an explicit record that it was considered and not adopted.
- A record of the repository-wide search performed in Step 6, showing every remaining `CAP-001` reference and confirming each is attributable to a specific track.
- ARB-DEC-001 itself, as the record of the Board's confirmation of this resolution direction.

---

## 11. Verification Procedure

**Status relative to Version 1.0: UPDATED**

The Architecture Review Board verifies completion of ACT-001 by confirming, against the Exit Criteria recorded in Section 1:

1. That a governance action exists — the designation record produced under Step 4 — formally designating the Track B definition as authoritative, satisfying the Exit Criteria's "formally designates one definition as authoritative" disjunct.
2. That the repository-wide search evidence (Section 10) shows every remaining `CAP-001` reference is attributable to a specific track, with no repository document asserting the two definitions as identical, interchangeable, or unresolved.
3. That the Track B `CAP-001` lineage identified in Version 1.0 Section 3 remains unchanged, and that neither capability's identifier has been reassigned or renumbered, consistent with ARB-DEC-001's condition that identifier immutability remain unchanged.

Verification is satisfied only when all three conditions are confirmed against submitted evidence, consistent with the verification standard already established in Version 1.0.

---

## 12. Completion Recommendation

**Status relative to Version 1.0: UPDATED**

| Transition | Evidence Required |
|---|---|
| Identified → Approved | Already satisfied by the original ACT-001 approval; ARB-DEC-001 confirms the resolution direction is now Option 3. |
| Approved → Planned | An owner and target release are assigned to this Version 2.0 plan, consistent with the Architecture Action Register's fields for those attributes. |
| Planned → In Progress | Execution of the Implementation Plan (Section 7) begins under this Version 2.0. |
| In Progress → Implemented | Steps 2 through 5 of the Implementation Plan are complete; the designation record (and, if adopted, the `HB-001` note) exist. |
| Implemented → Verified | The repository-wide search evidence (Step 6) and the designation record (Step 4) are submitted and confirmed against the Verification Procedure (Section 11). |
| Verified → Closed | The Architecture Review Board records closure of ACT-001 in the Architecture Action Register, with Verification Evidence populated per the Governance Rules already established in that register. |

---

## Appendix A — Version Comparison Summary

| Section | Version 1.0 | Version 2.0 | Reason for Change |
|---|---|---|---|
| 1. Action Summary | Reproduced Register fields only | Adds version relationship and approved implementation direction | Records ARB-DEC-001 and this document's supersession relationship |
| 2. Objective | Success = single resolved identifier via reassignment | Success = formal designation record exists; no reassignment | ARB-DEC-001 adopts Option 3, not the reassignment approach |
| 3. Repository Scope | Capability matrix and dashboard require identifier edits | Capability matrix and dashboard require no substantive change; new designation record is primary artifact | Option 3 requires no reassignment |
| 4. Current State Analysis | Identifier-permanence rule not yet discovered | Identifier-permanence rule confirmed governing and unexcepted | Discovered during Version 1.0 execution; settled by ARB-DEC-001 |
| 5. Impact Assessment | Matrix, dashboard, and release doc require edits | No existing document requires substantive edits; one new record created | Option 3 avoids reassignment-driven edits |
| 6. Recommended Implementation Approach | Reassign Track A identifier within its domain block | Formally designate Track B as authoritative; reassign nothing | Direct implementation of ARB-DEC-001 §3 |
| 7. Implementation Plan | Steps center on locating and applying a new Track A identifier | Steps center on drafting and adopting the designation record | Reassignment steps are no longer applicable |
| 8. Validation Checklist | Confirms reassignment applied correctly | Confirms designation record adopted and no reassignment occurred | Reflects the revised plan |
| 9. Risks | Risks of missing a reference during reassignment | Risks of an under-specified designation mechanism and residual scope-awareness need | Reassignment risks no longer apply; Option 3's own risks (per the Decision Review Package) apply instead |
| 10. Evidence Required | Updated matrix, dashboard, release doc, search record | Designation record, unchanged-document confirmation, search record | Reflects the revised set of required artifacts |
| 11. Verification Procedure | Confirms distinct-identifier resolution | Confirms formal-designation resolution | Exit Criteria's alternate disjunct is now the basis for verification |
| 12. Completion Recommendation | Transition evidence tied to reassignment steps | Transition evidence tied to designation-record steps | Reflects the revised Implementation Plan |
