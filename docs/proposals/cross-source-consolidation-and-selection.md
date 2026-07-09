# Design Proposal — Cross-Source Consolidation and Artifact Selection

**Status:** Proposal. Not approved. No code written.
**Origin:** CAP-074B root cause analysis — see `docs/reviews/cap-074b-requirement-evidence-investigation.md`
**Scope:** Consolidation Engine grouping, and the artifact-selection rule that consumes it.
**Requires:** A new ADR before any implementation. This document does not amend `docs/architecture/` or any existing ADR.

---

## 1. Problem

The Requirement Intelligence Layer ingests three sources and reasons over exactly one consolidated artifact at a time. Today that artifact is always single-source, and always SonarQube.

Measured on a live API run (28 JIRA issues, 46 ZAP alerts, 301 Sonar issues → 375 `SourceArtifact`s):

- 47 consolidated artifacts produced.
- **0 contain more than one source.**
- The selected artifact contained 0 functional, 0 security, 71 quality artifacts.
- 74 of 375 artifacts (all JIRA and all ZAP evidence) cannot influence any analysis.

The platform's stated purpose is to derive requirements from the *intersection* of functional intent, security findings, and code quality. It currently cannot express that intersection at all.

### 1.1 Mechanism

`consolidation_rules.py:derive_grouping_key` applies a first-match cascade — `component → tag → endpoint → risk` — and only `SonarMapper` populates `component`. Each source therefore matches a different rung:

| Source | Rung matched | Resulting key |
|---|---|---|
| SonarQube | `component` | `cons-component-<file path>` |
| OWASP ZAP | `tag` | `cons-tag-<alert tag>` |
| JIRA | `endpoint` | `cons-endpoint-<issue self URL>` |

The dimension is embedded in the group's identity, so two artifacts matching different rungs can never collide, however related they are in reality. Worse, JIRA's fallback is its per-issue `self` REST URL — unique by construction — so 28 issues yield 28 singleton groups.

`scripts/run_requirement_analysis.py:_select_consolidated` then ranks by total artifact count and takes the top one. SonarQube contributes 80% of all artifacts, concentrated per file. A Sonar group always wins; a JIRA singleton can never win.

### 1.2 What is *not* wrong

Worth stating plainly, because it shapes the fix. The connectors are correct. The mappers are correct — each renders faithfully what its source actually provides, and neither JIRA nor ZAP has a native concept of "code component." The Prompt Builder is correct. The grouping cascade is deterministic, explainable, and does exactly what its docstring says.

**The defect is that the cascade's *output shape* — one dimension per artifact — cannot represent an artifact that belongs to several dimensions at once.** That is a modelling limitation, not a coding error, and it is why the fix requires an ADR rather than a patch.

---

## 2. Design constraints

Any solution must preserve the properties the Consolidation Engine currently guarantees, because downstream subsystems depend on them:

- **Deterministic.** Same input → same groups → same `consolidated_id`s → same selection. The golden-baseline and model-evaluation harnesses compare SHA-256 hashes across runs.
- **Explainable.** Every group carries a human-readable `consolidation_reason`. No AI, no heuristics that cannot be stated in a sentence.
- **No I/O, no source-specific branching** inside `consolidation_rules.py`.
- **Stable IDs.** `build_consolidated_id` must remain a pure function of the grouping key.
- **Backwards-compatible canonical model.** `ConsolidatedArtifact` is a frozen canonical model; fields may be added additively, never removed or retyped.

The correlation problem is genuinely hard: nothing in a ZAP alert or a JIRA issue *directly* names a Java source file. Any cross-source link must be inferred from a shared secondary attribute. This proposal deliberately does not pretend that inference is free.

---

## 3. Option A — Multi-dimensional grouping keys

Replace the first-match cascade with a **key set**: each artifact yields *every* dimension it can populate, not merely the first. Two artifacts group together when their key sets intersect on any dimension.

*Sketch, illustrative only:*

```
Sonar issue  → {component: BadLoginPage.java, tag: java:S2068}
ZAP alert    → {tag: cwe-525, endpoint: /login}
JIRA story   → {tag: login, endpoint: /login}
```

Here the ZAP alert and the JIRA story would merge on `endpoint: /login`.

**Strengths.** Minimal change to the mental model; grouping stays deterministic and explainable; a group's reason can state which dimension caused the merge.

**Weaknesses.** Intersection-based grouping is transitive, which invites runaway merging: if A shares a tag with B and B shares an endpoint with C, do A and C merge? Without a rule that forbids chaining, one giant group can swallow most artifacts. It also does nothing for the Sonar↔JIRA link, since neither shares any attribute with the other today. And `consolidated_id` would need redefining, since a group no longer has one dimension.

**Assessment.** Attractive but insufficient alone. It solves ZAP↔JIRA and leaves the more valuable Sonar↔JIRA link unaddressed.

---

## 4. Option B — An explicit correlation dimension

Introduce a **correlation key** that all three mappers can populate from data their sources genuinely carry, and group primarily on that.

The realistic candidates:

| Correlation basis | JIRA | ZAP | Sonar | Viability |
|---|---|---|---|---|
| Component / module | ✗ no native field | ✗ | ✓ file path | Requires JIRA `components` field to be populated by the team |
| Endpoint / URL path | ~ from issue text | ✓ scanned URL | ✗ | Sonar has no URL |
| Shared label / tag | ✓ labels | ✓ alert tags | ✓ rule tags | Vocabularies differ entirely |
| CWE identifier | ✗ | ✓ | ✓ security rules | Narrow: security findings only |
| Git blame / file path in issue | ~ if referenced | ✗ | ✓ | Fragile |

No single basis spans all three. The honest conclusion is that **cross-source correlation needs a mapping layer** — a declarative, human-curated table relating JIRA components to source paths and to URL prefixes.

**Strengths.** Explicit, auditable, deterministic. Correlation quality becomes a configuration concern rather than a heuristic. A team that maintains the table gets excellent grouping; a team that does not is no worse off than today.

**Weaknesses.** Requires curation and drifts as the codebase moves. Introduces a new configuration asset (registry-adjacent) and a new failure mode: a stale mapping silently mis-groups. It cannot bootstrap itself.

**Assessment.** The most defensible long-term answer, and the only one that can link Sonar to JIRA. Its cost is honest and visible rather than hidden in a heuristic.

---

## 5. Option C — Fix selection, not grouping

Leave the Consolidation Engine alone. Change what the analysis stage consumes: instead of one consolidated artifact, assemble an **evidence bundle** spanning several groups.

Two variants:

**C1 — Risk-ranked multi-artifact selection.** Select the top *N* groups by a composite score, and include all of them. Rank on `risk_level` first, then count, then ID — so a `critical` JIRA defect can outrank 71 `MAJOR` code smells. Use `related_artifact_ids` (already on the canonical model, currently always empty) to express the association.

**C2 — Coverage-guaranteed selection.** Require the bundle to contain at least one group from each source category that produced any artifact. This *guarantees* functional, security, and quality evidence all reach the prompt whenever they exist, without any correlation being inferred.

**Strengths.** Does not touch `consolidation_rules.py`. Fixes the user-visible symptom — the prompt sees all three sources — with the smallest blast radius and no new configuration. C2 in particular is a handful of lines and is trivially explainable. The prompt's three sections would populate naturally, because `RequirementPromptBuilder` already renders whatever it is handed.

**Weaknesses.** The bundle is a *union*, not a *correlation*: the model receives JIRA, ZAP, and Sonar evidence side by side without any assertion that they concern the same code. This risks a subtler failure than today's — the model may confabulate relationships between unrelated evidence, which is harder to detect than an obviously Sonar-only output. It also grows the prompt substantially (today's single artifact already consumes 5 973 tokens; an unbounded bundle would not fit), so bundle size must be capped, and the cap becomes a new tuning knob.

**Assessment.** The best immediate step. It delivers most of the user-visible value at a fraction of the risk, and it is independently useful whatever grouping strategy is chosen later.

---

## 6. Recommendation

**Sequence C2 → B, and treat A as a possible refinement of B.**

1. **First, fix selection (Option C2).** Guarantee that the evidence bundle spans every source category that produced artifacts, ranked by risk rather than raw count, with a token-aware cap. This restores the platform's core premise — reasoning over functional, security, and quality evidence together — without inventing correlations that the data does not support. It is small, testable, deterministic, and reversible.

2. **Then, invest in correlation (Option B).** Once all three sources reach the prompt, the question becomes whether they concern the *same* code. That is when a curated correlation table earns its cost, and only then can its benefit be measured against a working baseline.

3. **Consider Option A** as an implementation detail of B, if the correlation table proves too heavy and a multi-dimensional key with an explicit no-chaining rule turns out to suffice.

Doing B first would be a mistake: it is the largest change, its benefit is unmeasurable until selection stops discarding 46 of 47 groups, and it demands curation effort before anyone has seen the feature work.

### 6.1 Prerequisites, in order

Two changes should land before or alongside any of this, because they determine whether the fix can be evaluated at all:

- **Grounding validation.** CAP-074B established that five hallucinated requirements passed all 13 validation rules and the CP1 gate with zero findings. Once the prompt carries three sources instead of one, the surface for unsupported inference grows. A rule that rejects requirements citing no supplied artifact — which presupposes artifact traceability in the response schema — should precede any bundle work, or the platform will be unable to tell an improvement from a regression.

- **Prompt Governance wiring.** `RequirementPromptBuilder` reads `prompt_constants.py`, not `PromptRegistry`. Until that is corrected, no prompt version can actually be promoted into effect, and any prompt tuned for multi-source evidence cannot be deployed through governance.

### 6.2 Open questions for the ADR

1. Does `ConsolidatedArtifact` gain a bundle concept, or does the analysis stage accept a `list[ConsolidatedArtifact]`? The latter avoids touching a frozen canonical model.
2. How is bundle size capped — fixed count, token budget, or risk threshold? A token budget is most robust but couples selection to the provider.
3. Does `manifest.json` record the full bundle in `selectedArtifactId`, or a new `selectedArtifactIds` array? This affects the Execution Package contract and the golden-baseline hashes.
4. What is the `consolidation_reason` of a bundle, and does it remain a single explainable sentence?
5. Every golden-baseline SHA-256 will change. What is the re-baselining procedure, and how is the old baseline retained for comparison?

---

## 7. Explicitly out of scope

This proposal changes nothing. It does not amend the Consolidation Engine, the canonical models, the Connector Framework, Validation, CP1, the Execution Package, or Prompt Governance. It proposes no prompt modification. Implementation of any option above requires a new ADR and its own milestone.
