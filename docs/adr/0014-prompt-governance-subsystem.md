# ADR-0014 — Prompt Governance Subsystem: Elevating Prompts to First-Class Governed Assets

- **Status:** Accepted
- **Date:** 2026-07-08 (Proposed) · 2026-07-08 (Accepted)

## Problem

The Prompt Framework (CAP-011) is implemented, tested, and in Production use — but it lacks
the architectural governance maturity that the Validation and CP1 subsystems have reached.
Concretely:

1. **No canonical models.** Prompt identity is scattered across `PROMPT_VERSION` (a constant),
   ad hoc SHA-256 calculation in `ManifestBuilder`, and undeclared lifecycle state.

2. **No governed lifecycle.** There is no governed vocabulary for whether a prompt is `Draft`,
   `Experimental`, `Approved`, `Production`, `Deprecated`, or `Archived`.

3. **No explicit registry.** Prompt construction is ad hoc (`RequirementPromptBuilder`); there
   is no sealed registry that guarantees the governed prompt set is fixed for the lifetime of
   a component.

4. **No file integrity contract.** The SHA-256 in `manifest.json` is an observation; it is not
   an architectural fingerprinting guarantee with a known-good baseline stored in a versioned
   manifest.

5. **No compatibility metadata.** No prompt declares which Normalization, Validation, CP1,
   Golden Dataset, or Output Schema versions it was verified against.

6. **No semantic versioning rules.** There are no governed rules for when a PATCH / MINOR /
   MAJOR version bump is required.

7. **No architecture document.** CAP-011 is noted in the Architecture Freeze Index as
   "No dedicated architecture document" and "Not Frozen (stable)".

The Validation subsystem (CAP-040–052) and the CP1 subsystem (CAP-060–068) both resolved the
same class of problem by introducing canonical models, an explicit registry, a governed lifecycle,
and an architecture document.  Prompts need the same treatment.

## Context

Design-review findings, from repository evidence:

1. **No contradictions.** The Prompt Framework (CAP-011) is "Not Frozen (stable)" in the
   Architecture Freeze Index.  No frozen contract depends on the internal structure of
   `prompts/` beyond the public surface (`PromptRequest`, `RequirementPromptBuilder`,
   `PROMPT_VERSION`).  The new subsystem is purely additive.

2. **Provider agnosticism is already established.** The `prompts/` package explicitly knows
   nothing about Gemini, Azure OpenAI, Anthropic, or any other provider.  This invariant must
   be preserved.

3. **The Validation/CP1 pattern is the reference.** Both subsystems follow:
   `Architecture → Framework → Canonical Models → Implementation → Testing → Frozen`.
   The prompt subsystem should advance along the same lifecycle.

4. **Prompt wording must not change.** The existing `prompt_constants.py` constants define the
   governed prompt.  They are byte-for-byte frozen by this ADR.  The ADR introduces governance
   *around* them, not *of* them.

5. **Filesystem scanning and reflection are prohibited.** The existing registry and CP1 registry
   both use explicit registration.  This must apply to the prompt registry too.

## Decision

Elevate prompts to a **first-class governed subsystem** within `requirement_intelligence/prompts/`
by introducing:

### A. Canonical Models (`models/`)

Four immutable Pydantic/dataclass models constitute the canonical identity of every governed prompt:

| Model | Role |
| ----- | ---- |
| `PromptVersion` | Semantic version value object with ordering and bumping rules |
| `PromptLifecycle` | Governed lifecycle StrEnum: `Draft → Experimental → Approved → Production → Deprecated → Archived` |
| `PromptCompatibility` | Explicit 5-dimension compatibility declarations (metadata only, no runtime enforcement) |
| `PromptMetadata` | Complete descriptive identity: `prompt_id`, `name`, `version`, `owner`, `lifecycle`, `description`, `sha256`, `compatibility`, `release_introduced`, `release_deprecated` |
| `PromptDefinition` | Aggregate root: `PromptMetadata` + immutable template `content` |

### B. Governance Framework (`framework/`)

| Component | Role |
| --------- | ---- |
| `PromptRegistry` | Explicit, deterministic, `OPEN → SEALED` registry (mirrors `ValidationRegistry` and `CP1CriterionRegistry`) |
| `PromptLoader` | File-based loader with SHA-256 integrity verification against `versions/manifest.json` |
| Exception hierarchy | `PromptFrameworkError → PromptRegistryError / PromptLoaderError / PromptNotFoundError` |
| `build_prompt_registry()` | Canonical composition entry point (explicit, sealed) |

### C. Versioned Storage (`versions/`)

| Artifact | Role |
| -------- | ---- |
| `requirement_analysis_v1.0.0.txt` | Byte-for-byte copy of the assembled static template (prompt_constants assembled in order, `{artifact_context}` placeholder) |
| `manifest.json` | Machine-readable index of every versioned file and its SHA-256 fingerprint |

### D. Governing document

`requirement_intelligence/prompts/README.md` is the architecture document for this subsystem,
mirroring `validation/README.md` and the existing governance pattern.

### E. Versioning rules

| Change | Bump |
| ------ | ---- |
| Wording clarification / editorial / punctuation | PATCH (`1.0.0 → 1.0.1`) |
| Additive section — output schema compatibility preserved | MINOR (`1.0.0 → 1.1.0`) |
| Removal / restructuring / new/removed output schema key | MAJOR (`1.x.x → 2.0.0`) |

### F. Compatibility dimensions (Phase 7)

| Dimension | Governed by |
| --------- | ----------- |
| `normalization_version` | `NORMALIZATION_CONTRACT_VERSION` (response-normalization-contract.md) |
| `validation_version` | `DEFAULT_VALIDATION_CONTRACT_VERSION` (ai-response-validation.md) |
| `cp1_version` | `DEFAULT_CP1_CRITERIA_CONTRACT_VERSION` (ADR-0012) |
| `golden_dataset_version` | `GOLDEN_DATASET_VERSION` (golden-baseline.md) |
| `output_schema_version` | Governed JSON response schema version |

### G. Regression contract (Phase 10)

Every prompt wording change must:
1. Pass the Golden Baseline (`tests/productization/test_golden_baseline.py`).
2. Preserve the output schema — unless the change is a major version bump.
3. Pass all Validation rules on the golden response.
4. Pass CP1 on the golden response.
5. Update `PromptCompatibility` when a referenced subsystem version changes.

This is a governance contract, not runtime enforcement.

### H. Architectural invariants

1. `prompt_constants.py` wording is byte-for-byte frozen unless a governed version bump is performed.
2. `RequirementPromptBuilder` is not modified by this subsystem.
3. No provider-specific code in any `prompts/` module.
4. No filesystem discovery — all registrations are explicit.
5. No reflection / dynamic loading.
6. Registry seals immediately after composition — no late registration.

## Consequences

### Positive

- Prompts advance to the same governance maturity level as Validation and CP1.
- Every prompt carries an immutable, verified SHA-256 fingerprint.
- Lifecycle state is explicitly declared and machine-readable.
- Compatibility dependencies are explicit metadata records, not tribal knowledge.
- The `PromptRegistry` provides a deterministic, sealed lookup that mirrors the
  `ValidationRegistry` and `CP1CriterionRegistry` patterns.
- Adding a future prompt (`cp1_assist_v2`, `feature_engineering_v1`) is a
  single `registry.register(...)` call in `composition.py`.

### Neutral

- The existing `RequirementPromptBuilder`, `PromptRequest`, `prompt_constants.py`,
  and `prompt_templates.py` are **unchanged**.
- No provider knows about prompt versions; provider agnosticism is preserved.
- No runtime enforcement of compatibility metadata — it is declarative only.

### Negative / Risks

- None identified.  The subsystem is additive; no existing contract is altered.

## Alternatives considered

**1. Continue with the current approach (no canonical models, no registry)**
Rejected: the Architecture Freeze Index identifies the Prompt Framework as having
"No dedicated architecture document" and "Not Frozen (stable)".  As downstream
capabilities (Feature Engineering, Test Generation) are built on top of prompts,
the absence of governance will become a liability.

**2. Embed metadata in prompt files (YAML front matter)**
Rejected: violates the "Every concept has exactly one canonical owner" principle.
The established platform pattern (Validation, CP1) is canonical Python models.
Mixing governance into text files creates a parsing dependency and two places
that could diverge.

**3. Auto-discover prompts via filesystem scanning**
Rejected: explicitly prohibited by the platform architecture ("No reflection, no
dynamic loading, no filesystem scanning" — `ValidationRegistry` and
`CP1CriterionRegistry` design notes).

## Capability tracking

| Capability | CAP ID |
| ---------- | ------ |
| Prompt Governance Subsystem (umbrella) | CAP-071 |
| Prompt Canonical Models | CAP-072 |
| Prompt Governance Framework (registry, loader, composition) | CAP-073 |
