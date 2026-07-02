# ADR 0005 — Schema Enumeration Deferral (SCHEMA-0003)

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

Implementing the Schema layer in Rule-Catalog order reached `SCHEMA-0003`
(EnumerationsRule — "Each enumerated field holds a permitted value", Validation Rule
Catalog §9.3). The mandatory pre-implementation design review found that **the current
governed response schema contains no enumerated field**, so the rule has **nothing to
validate**.

The evidence is unambiguous and repository-sourced:

- **The governed response schema** (`requirement_intelligence/prompts/prompt_constants.py`,
  `JSON_RESPONSE_REQUIREMENTS`) is exactly:

  ```json
  { "summary": "", "functional_requirements": [], "security_requirements": [],
    "quality_requirements": [], "risks": [], "recommendations": [] }
  ```

  One string (`summary`) and five string-arrays. The output rule states *"Every array
  element must be a string statement"* (`OUTPUT_REQUIREMENTS`). **No field carries an
  enumerated value domain.** `SCHEMA-0001` owns the non-collection existence
  (`summary`), `SCHEMA-0002` owns the field types, and `SCHEMA-0004` will own the
  required-collection existence — leaving `SCHEMA-0003` with no governed field to bind.

- **The Reasoning Contract** (`docs/architecture/ai-reasoning-contract.md` §5) defines a
  *"confidence tier"*, but it is an **internal evidence-weighting concept used during
  reasoning**, never emitted as a field in the response structure. It is not a Schema
  input and does not create an enumerated response field.

- **The Validation Rule Catalog's enumeration wording** (§8.3, §9.3, and the worked
  example at §8.3 referencing *"a confidence field holding a value outside its permitted
  set"*) is **illustrative** — it describes what `SCHEMA-0003` *would* validate *if* such
  a field existed. It reserves an identity; it does not declare that the current schema
  contains an enumerated field.

- **The Validation Canonical Models** define no enumerated response field (no enumeration
  references).

- **Existing code enums** (`requirement_intelligence/models/enums.py` —
  `SourceSystem`, `SourceCategory`, `SourceType`, `RiskLevel`) govern **input source
  artifacts** (ingestion), never the AI **response** `normalized_structure`. They are not
  a valid Schema-layer enumeration source.

- **Formal, published schema validation** is an explicit **future capability** (AI
  Response Validation Architecture §14), not a present governed source.

Therefore `SCHEMA-0003` could only be implemented today by **inventing** an enumerated
field and its permitted-value domain — implementation driving architecture, which the
platform's freeze philosophy prohibits (the same reasoning that produced ADR-0002,
ADR-0003, and ADR-0004: architecture is decided before implementation, never silently
inside a rule).

This is a **governance decision**, not an implementation task. This ADR records the
intentional deferral so the Schema layer can proceed to `SCHEMA-0004` without leaving an
undocumented gap.

## Decision

1. **`SCHEMA-0003` (EnumerationsRule) is a permanently reserved catalog identity.** Its
   Rule ID is fixed forever and is **never renumbered, reused, or retired** (Validation
   Rule Catalog §4.3, §4.4). It remains lifecycle **Approved** (an accepted catalog
   identity) and is **not** advanced to **Implemented**.

2. **Its implementation is intentionally deferred.** `SCHEMA-0003` becomes implementable
   **only after a governed response enumeration exists** — i.e. a response field with a
   governed, versioned permitted-value domain owned by exactly one frozen artifact.

3. **No rule may invent the concern.** No implementation may fabricate an enumerated
   response field, reuse an unrelated (input-side) enum, or infer permitted values from
   prompt wording. Introducing a governed response enumeration is itself an
   architecture change requiring its own approved ADR.

4. **The Schema layer proceeds to `SCHEMA-0004` (RequiredArraysRule).** `SCHEMA-0004`'s
   concern — the existence of the five required collections — is fully governed by the
   current schema and is the next Schema milestone.

> **Architectural principle established by this ADR**
> **Enumeration validation requires a governed enumeration.** A reserved rule identity
> may legitimately exist before its governed concern exists; the rule is implemented
> only when the architecture supplies the concern, never before.

## Clarifications

To prevent misreading this deferral, the following are stated explicitly:

- **This is not an architecture defect.** The Catalog correctly reserves `SCHEMA-0003`;
  reserving an identity ahead of need is deliberate catalog discipline (Catalog §4.4,
  §9.10).
- **This is not a missing implementation.** There is no concern to implement; an empty
  rule would validate nothing and could only exist by inventing a field.
- **This is not technical debt.** Nothing is owed, deferred-and-forgotten, or working
  around a shortcut. No code exists to remediate.
- **This is intentional governance.** The deferral is a recorded, reviewable decision
  with explicit future activation conditions.

## Permanent architectural invariants

These invariants are **frozen** by this ADR and apply platform-wide:

1. **A validation rule identity may exist before its governed concern exists.** Reserving
   a `<LAYER>-NNNN` identity ahead of the concern it will validate is valid architecture,
   not an omission.
2. **Reserved rule identities are valid architecture.** A reserved-but-unimplemented rule
   is a legitimate, stable state — it is neither a defect nor debt.
3. **A rule must never invent a governed concern.** Implementation conforms to
   architecture; it never creates the thing it is supposed to validate.
4. **Enumeration validation requires a governed enumeration.** `SCHEMA-0003` is
   implementable only when a governed, versioned, single-owner response enumeration
   exists.
5. **Example values inside architecture documents are illustrative unless explicitly
   declared normative.** A worked example (e.g. a "confidence field" in Catalog §8.3)
   does not, by itself, declare a governed field.
6. **No implementation may introduce enumerated response fields outside an ADR.** A new
   governed response enumeration is a frozen-schema change and requires its own approved
   ADR (Prompt Framework, Reasoning Contract, and Rule Catalog aligned as needed).

## Alternatives considered

- **A — Invent a response enumeration** (add a `confidence`/`priority`/`severity` field
  with a fabricated permitted-value set so `SCHEMA-0003` has something to check).
  **Rejected:** implementation driving architecture. Fabricating a governed field inside
  a rule (or to justify a rule) violates the freeze philosophy that produced ADR-0002…4.
- **B — Reuse unrelated enums** (bind `SCHEMA-0003` to `models/enums.py`, e.g.
  `RiskLevel`). **Rejected:** ownership violation. Those enums govern **input source
  artifacts**, not the AI response `normalized_structure`; Schema validates the response
  shape only (Schema Validation Implementation Contract §4, §5).
- **C — Infer enumerations from prompt wording** (derive a permitted-value set from the
  field-guidance prose). **Rejected:** prompt text is guidance, **not** a governed,
  versioned enumeration definition; inferring a value domain from prose is inventing
  architecture without governance.
- **D — Chosen: defer `SCHEMA-0003` as a permanently reserved identity; proceed to
  `SCHEMA-0004`.** **Accepted:** it preserves the reserved identity, invents nothing,
  keeps every concern to exactly one governed owner, and records explicit activation
  conditions — the disciplined, additive-growth path (Catalog §9.10).

## Consequences

- ✅ `SCHEMA-0003` remains **Reserved · Deferred · Awaiting governed enumeration** — a
  valid, recorded state; its Rule ID is frozen and never reused (Catalog §4.3).
- ✅ **`SCHEMA-0004` (RequiredArraysRule) becomes the next Schema implementation
  milestone.** Its concern is fully governed today.
- ✅ The Catalog's "every concern has exactly one owner" and "grow additively via
  governance" invariants are upheld; nothing is invented.
- ✅ No frozen contract is altered: the Rule Catalog, Schema Validation Implementation
  Contract, Prompt Framework, Reasoning Contract, `ParsedResponse`, and `ValidationInput`
  are unchanged.
- ⚠️ **Version impact:** this ADR **records a governance decision and changes no rule
  concern, severity, blocking, identity, or canonical model shape.** It therefore forces
  **no** version bump — not the **Rule Catalog Version**, the **Validation Contract
  Version**, the **Validator Version**, nor any **Rule Version** (Catalog §20). It is a
  governance clarification of an already-reserved identity. (A *future* ADR that
  introduces a governed response enumeration and activates `SCHEMA-0003` will advance the
  appropriate versions at that time.)
- ⚠️ **Governance alignment applied under this ADR** (no implementation change; see
  "Governance alignment" below).

## Future activation conditions

`SCHEMA-0003` may be implemented **only** when **all** of the following hold, each
established through an approved ADR:

1. **A governed response enumeration exists** — at least one response field carries an
   explicit permitted-value domain.
2. **A versioned source of truth exists** for that enumeration (a governed, versioned
   definition — e.g. an injected/formal schema per AI Response Validation §14).
3. **Ownership is defined** — exactly one frozen artifact owns the enumeration domain
   (single-owner invariant).
4. **The Prompt Framework is updated** so the AI is required to emit the enumerated
   field with values from the governed domain.
5. **The Reasoning Contract is aligned** where the enumeration reflects a reasoning
   concept (so response semantics and reasoning semantics agree).
6. **The Rule Catalog is updated if necessary** to bind `SCHEMA-0003`'s concern to the
   now-existing governed enumeration.

Only when these conditions are met may `SCHEMA-0003` move from **Reserved · Deferred**
to **Implemented**, under the same Schema-layer engineering discipline as
`SCHEMA-0001`/`SCHEMA-0002`.

## Governance alignment

As a consequence of this ADR, the following **governance** documents are updated so the
deferral is recorded consistently (no code, no architecture-contract, and no
implementation changes):

- `docs/architecture/validation-rule-catalog.md` — §9.3: a **status note** marks
  `SCHEMA-0003` as **Reserved · Deferred · Awaiting governed enumeration** (ADR-0005).
  The Rule ID, its position, and the numbering are unchanged.
- `docs/governance/architecture-freeze-index.md` — §6 Relationship to ADRs and the
  Validation Rule Catalog artifact row (§4) record ADR-0005 as the governing decision for
  the `SCHEMA-0003` deferral. (§4.1 Freeze History is unchanged: it tracks *frozen
  artifact* lifecycles, and `SCHEMA-0003` is a reserved rule identity, not a frozen
  artifact.)
- `docs/governance/platform-capability-matrix.md` — CAP-044 (Schema Layer) notes record
  the `SCHEMA-0003` deferral and that `SCHEMA-0004` is the next Schema milestone.
- `docs/governance/architecture-coverage-dashboard.md` — the readiness notes record the
  `SCHEMA-0003` deferral (no coverage checkmark changes).

## Scope note

This ADR decides **only** the intentional deferral of `SCHEMA-0003` and the permanent
invariants that justify it. It does **not** implement any rule, does **not** create
`EnumerationsRule` or its tests, does **not** change the Validation Framework, the Schema
contracts, the Prompt Framework, the Reasoning Contract, `ParsedResponse`, or
`ValidationInput`, and invents **no** enumeration. It changes **no** code and **no** rule
identity or number.
