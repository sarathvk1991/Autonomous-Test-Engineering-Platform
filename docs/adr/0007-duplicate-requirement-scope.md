# ADR 0007 — Duplicate Requirement Detection Scope (CONTENT-0002)

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

The mandatory design review for **`CONTENT-0002` (DuplicateRequirementRule)** halted on
a genuine architectural under-specification: the frozen documents state the *concern*
but not its *scope*.

- Validation Rule Catalog §9.5: `CONTENT-0002 | DuplicateRequirementRule | `**`Requirements
  are not duplicated.`**
- Validation Rule Catalog §8.5: "Detect … **duplicated entries** …; requirements are not
  duplicated."
- ADR-0006: classifies `CONTENT-0002` **Implementable** ("duplicate governed strings are
  observable") — but does not define the scope.

`CONTENT-0002` inspects three governed requirement collections
(`functional_requirements`, `security_requirements`, `quality_requirements`). "Requirements
are not duplicated" is **scope-silent**: it does not say whether duplication is evaluated
**within each collection independently** or **across all three collections pooled**. The two
readings produce opposite verdicts for the same input:

```json
{ "functional_requirements": ["X"], "security_requirements": ["X"] }
```

- **Within-collection:** `X` occurs once per collection → **no finding**.
- **Across-collections:** `X` is duplicated across the pool → **a finding**.

The contrast that proves the silence is real: the platform's *only other* duplicate rule
carries an **explicit** scope — `SYNTAX-0002` (Catalog §9.2): *"No field identifier is
duplicated **within a structural object**."* When the architecture wants a bounded scope,
it states it. `CONTENT-0002` carries no such qualifier, so neither reading is uniquely
determined by the frozen text.

Because the scope is undefined, the design review correctly **stopped** rather than
silently choosing (Catalog §3.1 forbids duplicated responsibility; the freeze process
forbids resolving architecture inside an implementation). This ADR freezes the scope so
`CONTENT-0002` becomes fully specified and implementable.

### Design review findings

1. **Is the ambiguity genuine?** **Yes.** "Requirements are not duplicated" does not fix a
   scope; two defensible, behaviourally-divergent readings exist.
2. **Does the Rule Catalog define duplicate scope?** **No.** §9.5 and §8.5 state the
   concern, not the scope.
3. **Does any architecture document define duplicate scope?** **No.** No frozen document
   scopes `CONTENT-0002`. (`SYNTAX-0002` scopes only *its own* concern.)
4. **Would silently choosing a scope violate the Freeze process?** **Yes.** It would bake
   an undocumented ownership decision into code — the anti-pattern ADR-0002/0003/0004
   exist to prevent.
5. **Is an ADR the correct governance mechanism?** **Yes.** The Catalog is frozen and grows
   only through governance; clarifying a rule's scope without changing its identity,
   severity, or blocking is exactly an ADR's remit.

No contradiction was found among the frozen documents — only an under-specification. An ADR
resolves it additively.

## Decision

**`CONTENT-0002` (DuplicateRequirementRule) evaluates duplicate requirement statements
independently within each governed requirement collection. The collections are never
pooled.**

- The governed requirement collections are exactly: `functional_requirements`,
  `security_requirements`, `quality_requirements`.
- Duplication is evaluated **within one collection at a time**; each collection is assessed
  independently of the others.
- A statement appearing **once in each of several collections is not** a `CONTENT-0002`
  finding.
- **Cross-collection duplication is outside `CONTENT-0002`'s ownership.** If that capability
  is ever required, it will receive its **own** architectural identity in a future ADR and
  a new Rule Catalog entry — never by widening `CONTENT-0002`.

This ADR fixes only the **scope** of an existing catalogued rule. It changes **no** rule
identity, name, severity, blocking, layer, or number, and introduces **no** new rule.

## Architectural justification

- **Preserves Catalog §3.1 (single ownership).** A within-collection scope keeps
  `CONTENT-0002`'s concern local and singular — the same statement listed twice **in one
  collection**. It cannot collide with any other rule's concern.
- **Preserves Content ownership (§8.5).** Content owns field-level value presence/validity
  of items that exist; a repeated entry *inside a collection* is precisely a local content
  defect. Pooling collections would reach beyond a single collection's content.
- **Avoids overlap with Structural (§8.4).** Across-collection detection compares *between
  containers*, which is a **cross-container relationship** — Structural's family, not
  Content's. Within-collection detection never crosses a container boundary.
- **Avoids overlap with Reasoning (§8.8).** Reasoning owns "duplicated conclusions across
  the output." Pooling requirement statements across collections drifts toward that
  cross-output semantic concern. A within-collection, byte-exact scope stays clear of it.
- **Matches `CONTENT-0001`'s per-collection iteration model.** `EmptyRequirementRule`
  already iterates each requirement collection independently; `CONTENT-0002` uses the same
  per-collection model, keeping the Content rules structurally consistent.
- **Matches the `SYNTAX-0002` precedent.** The platform's established duplicate-scoping
  pattern is "**within a structural object**" (§9.2). A requirement collection is the
  analogous local container; within-collection scope follows the precedent rather than
  inventing a new, broader one.
- **Keeps the Content layer purely local.** The rule reasons about one collection's entries
  only — no cross-container state, no pooled index.
- **Avoids inventing semantic relationships.** Duplication is **byte-exact identity within a
  collection**; no semantic equivalence, paraphrase, or similarity judgement is introduced
  (those are not Content's, and none is governed).

## Alternatives rejected

- **Alternative A — Evaluate across all requirement collections (pooled).** **Rejected:**
  it introduces **cross-container semantic relationships** that lie outside Content
  ownership — comparing entries *between* `functional_`, `security_`, and `quality_`
  collections is a cross-container concern (Structural, §8.4) that also drifts toward
  Reasoning's "duplicated conclusions" (§8.8). It would risk violating Catalog §3.1
  (single ownership) and would treat a statement legitimately serving two distinct
  requirement categories as a defect.
- **Alternative B — Leave the scope undefined.** **Rejected:** two implementers could
  legitimately build **incompatible** validators (one within-collection, one pooled),
  producing divergent verdicts for identical responses — defeating determinism and audit
  (Catalog §16). An undefined scope is not a stable architectural state.

## Ownership statement

**`CONTENT-0002` owns:**

> Duplicate requirement statements **within one governed requirement collection**.

**`CONTENT-0002` never owns:**

- duplicates **across** collections (a future, separately-catalogued capability, if ever
  needed);
- **semantic equivalence** or **paraphrase** detection;
- **reasoning similarity** (Reasoning, §8.8);
- **recommendation** duplication (`REASONING-0002`, §9.8);
- **risk** duplication.

## Architecture verification

- **No duplicated ownership.** Within-collection duplication is owned solely by
  `CONTENT-0002`; no other rule owns it (Catalog §3.1, §17).
- **No ownership gaps introduced.** Cross-collection duplication is explicitly declared
  *out of scope and unowned today*, reserved for a future ADR — a deliberate, recorded
  boundary, not a silent gap.
- **No layer crossing.** The scope stays within Content; it does not reach Structural
  (cross-container) or Reasoning (cross-output coherence).
- **Consistent with ADR-0003/0004/0005/0006.** Input contract unchanged (ADR-0003);
  existence/composition boundary unchanged (ADR-0004); no invented governed field
  (ADR-0005/0006 discipline honoured — duplication of *existing governed strings* is
  observable without enrichment).

## Consequences

- ✅ `CONTENT-0002` is now **fully specified**: identity/severity/blocking (Catalog §9.5,
  §14, §15) + **scope (this ADR)**. It is ready for a straightforward, additive
  implementation under the existing contracts.
- ✅ The implementation is mechanical: iterate each of the three requirement collections
  independently; within a collection, a statement that has already appeared is a duplicate
  occurrence → one `ValidationIssue` per duplicate occurrence; byte-exact identity, no
  trim/normalize/lowercase; defer on absent structure; raise only on absent
  `ParsedResponse`.
- ✅ A future cross-collection capability, if needed, has a clean home (a new Rule Catalog
  identity via a future ADR) without disturbing `CONTENT-0002`.
- ⚠️ **Version impact:** this ADR **clarifies the scope of an existing catalogued rule**
  without changing its concern's *meaning*, severity, blocking, identity, number, or any
  canonical model. It advances **no** version (Rule Catalog Version, Validation Contract
  Version, Validator Version, Rule Version all unchanged; Catalog §20). It is a governance
  clarification, recorded so implementations are deterministic.
- ⚠️ **Governance alignment applied** (no implementation, no framework, no contract
  changes; see "Governance alignment").

## Governance alignment

As a consequence of this ADR, the following governance/reference documents are updated so
the scope is recorded consistently (no code, no framework, no canonical-model, and no
contract changes):

- `docs/architecture/validation-rule-catalog.md` — §9.5: a **clarification note** records
  that `CONTENT-0002` is scoped **within each requirement collection** (ADR-0007). The Rule
  ID, name, concern statement, severity, and blocking are unchanged.
- `docs/governance/architecture-freeze-index.md` — §6 Relationship to ADRs records
  ADR-0007; the Validation Rule Catalog artifact row references it.
- `docs/governance/platform-capability-matrix.md` — the CAP-046 (Content Layer) note
  records the frozen `CONTENT-0002` scope.

## Scope note

This ADR decides **only** the duplicate-detection scope of `CONTENT-0002`. It does **not**
implement `CONTENT-0002` (or any rule), create tests, or change any code, framework,
`ValidationInput`, `ParsedResponse`, `ResponseValidator`, `ResponseNormalizer`, canonical
model, or the Validation Rule / Schema Implementation Contracts. It changes no rule
identity, number, severity, or blocking. Implementation of `CONTENT-0002` is a separate,
subsequent task under this frozen scope.
