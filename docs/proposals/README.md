# `docs/proposals/` — status index

This directory holds original Low-Level Design proposals — mostly PPTX decks authored outside
this repository, plus a few Markdown transcriptions of those decks. **None of these documents are
living design docs.** For a built layer, the current, authoritative design record is its
Accepted architecture-freeze ADR (`docs/adr/`) plus `docs/architecture/architecture-baseline-v2.md`
— not the proposal here. This index exists so a PPT in this directory is never mistaken for
current design.

Full reasoning and per-layer evidence: `docs/architecture/lld-review-findings.md`.

## Per-layer LLD proposals (PPTX decks + their Markdown transcriptions)

| Layer | Built? | File(s) | Status |
|---|---|---|---|
| L1 — Requirement Intelligence | Yes | `layer-1-requirement-intelligence-layer-lld.pptx` + `layer-1-requirement-intelligence-lld.md` | **PPT: superseded.** Original deck, contradicted on sources (HP ALM → real: JIRA), LLM provider (Azure OpenAI → real: Gemini), CP1 rules, and output artifacts. Retained for proposal history only. **MD: current, as-built** — written directly from code (not a deck transcription, since the deck was too stale to transcribe faithfully), timed with the mentor-item-#3 completeness work per the review's own lean (CAP-088, the traceability graph, resolved that item). See `layer-1-requirement-intelligence-lld.md` and `docs/architecture/lld-review-findings.md` §2. |
| L2 — Feature Engineering | Yes | `layer-2-feature-engineering-lld.pptx` + `.md` | **PPT: superseded.** Original proposal, superseded by [ADR-0043](../adr/0043-layer-2-feature-engineering-architecture-freeze.md) (Accepted) and the living record (`architecture-baseline-v2.md`). Retained for proposal history only. **MD: current** — a frozen transcription-plus-Reviewer's-note record, still accurate as of the last review; not a living doc, but not stale either. |
| L3 — Automation Engineering | Yes | `layer-3-automation-engineering-lld.pptx` + `.md` | **PPT: superseded.** Original proposal, superseded by [ADR-0044](../adr/0044-layer-3-automation-engineering-architecture-freeze.md) (Accepted) and the living record. Retained for proposal history only. **MD: current** — same disposition as L2's. |
| L4 — Suite Quality Governance | Yes | `layer-4-quality-governance-lld.md`, `layer-4-cp5-suite-integration-governance-design.md`, `layer-4-cp7-cp8-design.md` | **No PPT exists for this layer** (the source deck was reviewed but never committed here, unlike L2/L3 — documented in the first file's own header). All three Markdown documents are superseded by [ADR-0046](../adr/0046-layer-4-quality-governance-architecture-freeze.md) and [ADR-0047](../adr/0047-layer-4-cp7-cp8-freeze.md) (both Accepted) and the living record, but remain accurate as historical design-proposal records — not stale, not living. |
| L5 — Test Execution | No | `layer-5-execution-layer-lld.pptx` | **Forward design, not superseded.** Unbuilt layer; this deck is the only design input so far. Contains known staleness (HP ALM, Azure OpenAI, a CP7 label ADR-0047 has since reassigned to Layer 4) and depends on ADR-0039 (Execution Backend and CI/CD), which is **Proposed, not Accepted** — see findings §6. |
| L6 — Failure Intelligence & Self-Healing | No | `layer-6-failure-intelligence-&-self-healing-layer-lld.pptx` | **Forward design, not superseded.** Unbuilt layer. Its auto-remediation framing needs reconciling with the platform's bounded-remediation-then-human-gate pattern (ADR-0040) when Layer 6 is eventually designed — see findings §6 and mentor item #6. |
| L7 — Governance Dashboard | No | `layer-7-governance-dashboard-layer-lld.pptx` | **Forward design, not superseded.** Unbuilt layer. Assumes a per-run pipeline-stage shape that ADR-0036 §D5 leaves explicitly open (stage vs. standing service) — see findings §6 and mentor item #7. |

## Other proposals in this directory

The remaining files (`capability-contract-standard-*`, `continuous-improvement-framework.md`,
`cross-source-consolidation-and-selection.md`, `evidence-grounding-and-traceability.md`,
`executable-specification-engineering.md`, `governance-review-lifecycle-*.md`,
`knowledge-graph-framework.md`, `learning-framework.md`, `organizational-memory-framework.md`,
`quality-governance-framework.md`, `recommendation-framework.md`,
`repository-governance-reorganization-proposal.md`, `requirement-enhancement-framework.md`) are
cross-cutting Layer-1-sub-capability proposals, not per-layer pipeline LLDs. They were out of
scope for the LLD review and are not assessed by this index.
