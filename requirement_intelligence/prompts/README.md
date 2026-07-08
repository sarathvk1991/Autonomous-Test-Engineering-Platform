# Prompt Governance Subsystem

| Attribute | Value |
| --------- | ----- |
| Package | `requirement_intelligence.prompts` |
| Status | Production Ready |
| Version | `PROMPT_FRAMEWORK_VERSION` 1.0.0 |
| Governing ADR | ADR-0014 |
| Capability IDs | CAP-071 (subsystem) · CAP-072 (models) · CAP-073 (framework) |
| Architecture Document | This file |

---

## 1. Purpose

The Prompt Governance subsystem elevates prompts from implementation details
into **first-class, governed architectural assets**.  It provides:

- **Canonical models** — the immutable information structure that defines what
  a governed prompt *is* (identity, lifecycle, compatibility, SHA-256
  fingerprint).
- **Versioned storage** — prompt templates stored as immutable, versioned text
  files in `versions/` with a machine-readable index (`manifest.json`).
- **File integrity verification** — SHA-256 fingerprinting of every stored
  template, verified at load time.
- **Explicit registry** — an `OPEN → SEALED` lifecycle that mirrors the
  Validation Registry and CP1 Registry patterns.
- **Compatibility metadata** — every prompt declares the downstream subsystem
  versions it was verified against.
- **Governed lifecycle** — `Draft → Experimental → Approved → Production →
  Deprecated → Archived`.
- **Semantic versioning** — `PATCH / MINOR / MAJOR` rules tied to output-schema
  compatibility.

---

## 2. Package layout

```
requirement_intelligence/prompts/
│
├── __init__.py                     ← unified public API
│
├── prompt_constants.py             ← static prompt wording (UNCHANGED)
├── prompt_templates.py             ← section assembly helpers (UNCHANGED)
├── requirement_prompt_builder.py   ← PromptRequest builder (UNCHANGED)
│
├── models/                         ← Canonical models (Phase 3)
│   ├── __init__.py
│   ├── prompt_version.py           ← PromptVersion dataclass + PromptLifecycle
│   ├── prompt_compatibility.py     ← PromptCompatibility (5 dimensions)
│   ├── prompt_metadata.py          ← PromptMetadata (complete identity)
│   └── prompt_definition.py        ← PromptDefinition (aggregate root)
│
├── framework/                      ← Governance framework (Phase 4)
│   ├── __init__.py
│   ├── prompt_exceptions.py        ← Exception hierarchy
│   ├── prompt_registry.py          ← PromptRegistry (OPEN/SEALED)
│   ├── prompt_loader.py            ← File loader + SHA-256 verification
│   └── composition.py             ← Canonical composition entry point
│
└── versions/                       ← Versioned template storage (Phase 5)
    ├── requirement_analysis_v1.0.0.txt
    └── manifest.json               ← SHA-256 fingerprint index
```

---

## 3. Architecture

### 3.1 Layering

```
composition.py (assembly root)
        │
        ├── loads ──► PromptLoader ──► versions/manifest.json
        │                │              versions/*.txt
        │                │
        │                └── assembles ──► LoadedPrompt
        │
        ├── constructs ──► PromptMetadata (owns SHA-256, lifecycle, compat)
        │                    ├── PromptCompatibility
        │                    └── PromptLifecycle
        │
        ├── assembles ──► PromptDefinition (metadata + content)
        │
        └── registers in ──► PromptRegistry (OPEN → SEALED)
```

### 3.2 Separation of concerns

| Component | Knows about | Does NOT know about |
| --------- | ----------- | ------------------- |
| `prompt_constants.py` | Prompt wording | Governance, registry, versions |
| `RequirementPromptBuilder` | Assembly | Governance, registry, SHA-256 |
| `PromptLoader` | Files, SHA-256 | Registry, metadata, providers |
| `PromptRegistry` | Definitions, lifecycle | File system, providers |
| `PromptMetadata` | Identity, compatibility | File system, providers, runtime |
| `composition.py` | Assembly of the above | Analysis, Validation, CP1, LLM |

### 3.3 Provider agnosticism

**Nothing in this subsystem knows about any LLM provider.**  This is an
architectural invariant.  Prompts are assembled for a model; the subsystem
only governs the templates.  Provider bridging is `RequirementPromptBuilder`'s
responsibility (`requirement_prompt_builder.py`), which is unchanged.

---

## 4. Lifecycle

```
Draft → Experimental → Approved → Production → Deprecated → Archived
```

| State | Meaning |
| ----- | ------- |
| **Draft** | Authoring in progress. Not stable. Must not enter a production pipeline. |
| **Experimental** | Under evaluation. May be used in non-production runs. |
| **Approved** | Passed review. Authorised for production. Wording changes require a version bump. |
| **Production** | Active canonical version. Only one version of a prompt should be in this state. |
| **Deprecated** | Superseded. Consumers should migrate. No new usage permitted. |
| **Archived** | Retired. Retained for historical traceability only. |

---

## 5. Versioning rules (Phase 9)

Governed by `PromptVersion` and described in `prompt_version.py`.

| Change type | Bump | Output schema compat preserved? |
| ----------- | ---- | -------------------------------- |
| Wording clarification / punctuation / editorial fix | **PATCH** (`1.0.0 → 1.0.1`) | Yes |
| Additive section or instruction block | **MINOR** (`1.0.0 → 1.1.0`) | Yes |
| Removal / restructuring / new output schema key | **MAJOR** (`1.x.x → 2.0.0`) | No |

---

## 6. Compatibility (Phase 7)

Every `PromptMetadata` carries a `PromptCompatibility` record declaring which
downstream subsystem versions the prompt was verified against.

| Dimension | Governed by |
| --------- | ----------- |
| `normalization_version` | `NORMALIZATION_CONTRACT_VERSION` (response-normalization-contract.md) |
| `validation_version` | `DEFAULT_VALIDATION_CONTRACT_VERSION` (ai-response-validation.md) |
| `cp1_version` | `DEFAULT_CP1_CRITERIA_CONTRACT_VERSION` (ADR-0012) |
| `golden_dataset_version` | `GOLDEN_DATASET_VERSION` (golden-baseline.md) |
| `output_schema_version` | Governed JSON response schema version |

Compatibility is **metadata only** — it carries no runtime enforcement.

---

## 7. Prompt fingerprinting (Phase 8)

Every prompt carries a `sha256` field on its `PromptMetadata`.  This is the
SHA-256 of the raw bytes of the versioned template file
(`versions/requirement_analysis_v1.0.0.txt`).

The fingerprint is:
1. Computed at load time by `PromptLoader`.
2. Verified against the `manifest.json` recorded fingerprint.
3. Carried on `PromptMetadata.sha256` for downstream auditability.

This **template fingerprint** is distinct from the per-execution
`promptSha256` in `manifest.json` (execution package), which fingerprints the
fully assembled prompt (template + injected artifact context).

---

## 8. Regression contract (Phase 10)

Every prompt modification must:

1. **Pass the Golden Baseline** (`tests/productization/test_golden_baseline.py`).
2. **Preserve the output schema** unless the change is a major version bump.
3. **Pass Validation** (all Validation rules pass on golden response).
4. **Pass CP1** (CP1 verdict is PASS on golden response).
5. **Update compatibility metadata** (`PromptCompatibility`) when a referenced
   downstream subsystem version changes.

This is a **governance contract**, not runtime enforcement.

---

## 9. Usage example

```python
from requirement_intelligence.prompts import build_prompt_registry

# Build the sealed canonical registry
registry = build_prompt_registry()

# Look up the production prompt
definition = registry.get("requirement_analysis")
print(definition.metadata.version)      # "1.0.0"
print(definition.metadata.lifecycle)    # "production"
print(definition.metadata.sha256)       # 64-char hex SHA-256
print(definition.metadata.compatibility.normalization_version)  # "1.0"
```

---

## 10. Architecture boundaries (non-negotiable)

The following are **invariants**:

1. `prompt_constants.py` — wording must remain byte-for-byte identical unless
   a governed version bump is performed.
2. `RequirementPromptBuilder` — not modified by this subsystem.
3. No provider-specific code in any module under `prompts/`.
4. No filesystem discovery — all registrations are explicit.
5. No dynamic loading — no reflection, no `importlib`, no plugin scanning.
6. Registry seals immediately after composition — no late registration.
