# ADR 0004 — Schema vs Structural Ownership Boundary

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

Implementing `SCHEMA-0001` (RequiredSectionsRule — "All required sections are
present") surfaced a genuine, frozen-architecture **ownership conflict** between the
Schema and Structural layers of the Validation Rule Catalog.

The AI response schema the platform actually requires (the shape the prompt mandates,
`requirement_intelligence/prompts/prompt_constants.py`) has exactly these top-level
sections:

```json
{ "summary": "", "functional_requirements": [], "security_requirements": [],
  "quality_requirements": [], "risks": [], "recommendations": [] }
```

The frozen Catalog assigned **presence of these same top-level sections to two
different layers at once**:

- **Schema** — `SCHEMA-0001` "All required sections are present" (§9.3); §8.3
  "Detect **missing required sections**."
- **Structural** — `STRUCTURE-0001…0004` "The *summary / risks / recommendations /
  requirements* container is present" (§9.4); §8.4 "Detect **missing top-level
  sections**," with the worked example: *"An absent risks container is a **Structural**
  finding."*

An absent `risks` section would therefore be flagged by **both** `SCHEMA-0001` and
`STRUCTURE-0002` — a duplicated responsibility, which the Catalog itself defines as a
defect: *"A concern that is checked by two rules is a duplicated responsibility and a
defect in the catalog"* (§3.1). `SCHEMA-0001`'s concern ("all required sections
present") cannot be defined without either duplicating the Structural existence rules
or inventing a distinction the architecture does not state. A secondary mismatch
compounds it: the real schema has **three** requirement sections
(`functional_/security_/quality_requirements`) while Structural models a single
"requirements container" (`STRUCTURE-0004`).

This blocked `SCHEMA-0001` and required an architectural decision rather than a silent
per-rule resolution.

## Decision

Draw a single, non-overlapping ownership boundary between the two layers. **Every
concern belongs to exactly one layer.**

1. **Schema is the sole owner of machine-readable schema conformance.** This
   includes the **existence (presence) of every required property, section,
   container, and collection**, plus field **types**, enumerated **value domains**,
   and required **collections**. In one sentence: *does the well-formed structure
   match the declared, machine-readable schema — are the required things present and
   of the right shape?*

2. **Structural is the sole owner of document composition, hierarchy, and
   organization.** This includes parent–child **nesting**, **relationships** between
   sections, **ordering/grouping**, and overall **organization** of a document whose
   required parts already exist. In one sentence: *given that the required parts
   exist and conform, are they composed and organized correctly?*

3. **Property / section / container / collection existence belongs *only* to
   Schema.** **Structural no longer owns any JSON property-existence check.** A
   missing required property, section, container, or collection is a **Schema**
   finding, never a Structural one.

4. **The Structural existence rules are deprecated.** `STRUCTURE-0001`
   (SummaryExistsRule), `STRUCTURE-0002` (RisksExistsRule), `STRUCTURE-0003`
   (RecommendationsExistsRule), and `STRUCTURE-0004` (RequirementsExistsRule) are
   moved to **Deprecated** (Catalog §7). Their existence concern is now owned by
   Schema (`SCHEMA-0001` / `SCHEMA-0004`). Per Catalog §4.3 / §22 their Rule IDs are
   **frozen forever and never reused**; no successor reuses a `STRUCTURE-000N`
   identity for an existence concern. Concrete Structural **composition** rules
   (nesting/relationship/organization) are catalogued **additively** via a future
   ADR when needed; the Structural layer keeps its place in the pipeline order with
   no active rules until then.

5. **Within Schema, existence is partitioned by the datum's declared kind, so
   Schema's own rules never overlap.** A required **non-collection** property/section
   → `SCHEMA-0001` (RequiredSectionsRule); a required **collection** (array) →
   `SCHEMA-0004` (RequiredArraysRule); a field's **type** → `SCHEMA-0002`; an
   **enumerated value** → `SCHEMA-0003`. Each required datum's existence is owned by
   exactly one Schema rule.

6. **Schema vs Content is unchanged and remains distinct.** Schema owns
   *schema-shape existence and conformance* (is the required property present and of
   the declared kind?). Content owns *value meaning, quality, completeness, and
   range within already-conformant items* (is a present value empty, duplicated,
   lacking a description, or out of range?). Existence of a schema-declared property
   is Schema; the quality of its value is Content.

> **Architectural principle established by this ADR**
> **Existence and machine-readable conformance are Schema. Composition, hierarchy,
> and organization are Structural. Value meaning and quality are Content.** No two
> layers own the same concern.

## Consequences

- ✅ `SCHEMA-0001` now has a single, well-defined, non-overlapping concern: the
  existence of the required non-collection sections declared by the schema — with no
  collision against any Structural rule. It can be implemented without further
  architectural refinement.
- ✅ `SCHEMA-0004` cleanly owns the existence of required collections
  (`functional_/security_/quality_requirements`, `risks`, `recommendations`),
  resolving the three-requirements mismatch (each required array is a collection
  owned by `SCHEMA-0004`; `summary` is the non-collection section owned by
  `SCHEMA-0001`).
- ✅ The Catalog §3.1 "no duplicated responsibility" invariant is restored; every
  section-presence concern has exactly one owner.
- ✅ Structural is now unambiguously the composition/hierarchy/organization layer,
  free of existence concerns.
- ⚠️ `STRUCTURE-0001…0004` are Deprecated; their IDs are retired-in-place (frozen,
  never reused). The Structural layer has **no active rules** until composition rules
  are catalogued additively (future ADR). This is a valid state: the layer and its
  pipeline position remain; only concrete rules await definition.
- ⚠️ **Version impact:** this changes rule concerns and deprecates rules, so it
  advances the **Rule Catalog Version** (minor — deprecations + a governance
  clarification) and the **Validation Contract Version** (a change in what
  validation *means* at the Schema/Structural boundary), per Catalog §20.1 / §21.3.
  No `SCHEMA-000N` or `STRUCTURE-000N` **identity** is reused. No implemented rule
  changes behaviour (Transport and Syntax are untouched; no Schema/Structural rule
  is implemented yet), so no Validator Version bump is forced by code.
- ⚠️ **Documentation alignment applied under this ADR** (frozen docs, updated to
  reflect the non-overlapping ownership; see "Documentation alignment" below).

## Alternatives considered

- **A — Partition by aspect, keeping existence dual-owned "by lens" (Schema =
  schema-key set; Structural = per-container existence).** **Rejected:** it keeps
  section presence checked by two rules (§3.1 defect) and does not remove the
  conflict; it only renames it.
- **B — Make Structural the owner of top-level existence and re-scope Schema to
  types/enums only.** **Rejected:** it contradicts the very name and concern of
  `SCHEMA-0001` (RequiredSectionsRule) and `SCHEMA-0004` (RequiredArraysRule), and
  leaves "required collections present" (a schema-conformance concern) outside the
  schema-conformance layer.
- **C — Chosen: existence (all required properties/sections/containers/collections)
  → Schema; composition/hierarchy/organization → Structural; deprecate the
  Structural existence rules.** **Accepted:** it gives every concern exactly one
  owner, matches the machine-readable meaning of "schema conformance," preserves
  `SCHEMA-0001`/`SCHEMA-0004` as written, and cleanly re-scopes Structural.
- **D — Leave the conflict and resolve it inside `SCHEMA-0001`'s implementation.**
  **Rejected:** it would bake a silent, undocumented ownership decision into code,
  violating the freeze philosophy (architecture decided before implementation) — the
  same reasoning that produced ADR-0002 and ADR-0003.

## Documentation alignment

As a consequence of this ADR, the following frozen documents are updated so their
ownership is internally consistent and non-overlapping (no code changes):

- `docs/architecture/validation-rule-catalog.md` — §8.3 (Schema now explicitly owns
  required property/section/container/collection **existence** and machine-readable
  conformance); §8.4 (Structural re-scoped to composition/hierarchy/organization
  **only**; existence removed; worked example corrected so an absent container is a
  **Schema** finding); §9.3 (note the existence-ownership clarification); §9.4
  (`STRUCTURE-0001…0004` marked **Deprecated**, superseded by Schema).
- `docs/architecture/schema-validation-implementation-contract.md` — §3, §7, §10,
  and examples aligned so **existence (incl. containers) → Schema** and
  **composition/hierarchy/organization → Structural** (removing the earlier
  "container-with-nesting presence → Structural" phrasing).
- `docs/governance/architecture-freeze-index.md` — records ADR-0004 as the governing
  decision for the Schema/Structural boundary and the Structural-rule deprecations.

## Scope note

This ADR decides **only** the Schema ↔ Structural ownership boundary and the
consequent deprecation of the Structural existence rules. It does **not** define the
future Structural composition rules, does **not** change Transport or Syntax, does
**not** implement `SCHEMA-0001` (or any rule), and changes **no** code, framework,
canonical model, `ValidationInput`, or `ResponseNormalizer` contract.
