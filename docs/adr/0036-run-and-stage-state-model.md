# ADR-0036 — Run and Stage State Model

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing. It changes the run **directory naming convention** described in `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.4 (today: human-chosen `--execution-name`) — this is a recorded future intent, not an implemented change (Runtime status, below).
- **Governing design:** none. Evidentiary basis: `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.4/§3.1/§3.4 (today's synchronous CLI orchestration, no job model, no resumability) and `docs/architecture/execution-package.md` (the existing, unchanged artifact layout), both re-confirmed for this ADR.
- **Depends on:** ADR-0031 (Authoritative Layer Model — the seven layers this state model's stages cover); ADR-0032 (Layer 1 Capability Freeze — integrating this model into Layer 1 is its carve-out 2); ADR-0017 §D30 (the frozen Layer 1 internal pipeline order this ADR's stage list is drawn from, re-verified below).
- **Runtime status:** Not applicable. This is a **pure architecture freeze** — no code, `PlatformContext` method, or CLI flag is introduced or changed by this ADR. The existing Execution Package (`manifest.json` and its artifact files, per `docs/architecture/execution-package.md`) is explicitly **unchanged** and continues to work exactly as it does today; this ADR adds a state machine alongside it, not a replacement for it.

## Problem

`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.1 established: orchestration today is a synchronous CLI script (`scripts/run_requirement_analysis.py`) with **no job/task model, no state machine, and no resumability** — a failed run is simply re-invoked from the start. That gap is tolerable for a single-layer, single-process pipeline. It stops being tolerable the moment Layers 2–7 exist: a run that fails at Layer 5 (Test Execution) should not have to re-run Layer 1's Gemini call, and a future Layer 5 stage delegated to an external system (flagged as an open problem in ADR-0039) is inherently asynchronous in a way today's synchronous phase functions cannot represent at all.

## Decision

### `run_id` is the canonical identifier for one pipeline invocation

`run_id` becomes the run's directory name — the successor to today's ad hoc `output/executions/<execution-name>/` convention (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.4). The existing `--execution-name` CLI flag **remains**, but is redefined: it is recorded as a human-readable label *inside* the run (in `run_state.json`, D3), never used as the directory path itself. The exact `run_id` generation scheme (format, whether timestamp-derived or random) is deferred (TBD) — this ADR locks only that it is platform-assigned, unique per invocation, and is the path, not the label.

### `run_state.json` at the run root is the state machine

A new file, `run_state.json`, sits at the root of each run's directory (alongside the existing `manifest.json`) and is the **authoritative record of pipeline progress** for that run. It is additive: nothing about `manifest.json`, the artifact files it indexes, or the checksum mechanism changes.

### Stage statuses

Every stage carries exactly one of: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `SKIPPED`.

### Stages — Layer 1's existing internal phases, plus one slot per Layer 2–7

Re-verified against `docs/adr/0017-quality-governance-framework.md` §D30 and `docs/adr/0020-platform-evolution-roadmap.md` Stage 4/Stage 10 (the frozen live pipeline order and the Layer 2 sub-capability order), and against ADR-0033's package renames:

| # | Stage | Governing ADR | Status today |
|---|---|---|---|
| 1 | Engineering Context Orchestration | ADR-0015 | Live |
| 2 | Requirement Analysis | CAP-014 | Live |
| 3 | Requirement Enhancement | ADR-0018 | Live |
| 4 | Grounding | ADR-0016 | Live |
| 5 | Validation | (pre-ADR architecture docs) | Live |
| 6 | CP1 | ADR-0011/0012/0013 | Live |
| 7 | Requirement Quality Governance *(renamed, ADR-0033)* | ADR-0017 | Live |
| 8 | Recommendation | ADR-0019 | Live |
| 9 | Execution Package (write) | CAP-020/022 | Live |
| 10 | Continuous Improvement *(Layer 1 sub-capability, ADR-0031)* | ADR-0022 | Live |
| 11 | Knowledge Graph *(Layer 1 sub-capability, ADR-0031)* | ADR-0023 | Live |
| 12 | Organizational Memory *(Layer 1 sub-capability, ADR-0031)* | ADR-0027 | Live |
| 13 | Learning *(Layer 1 sub-capability, ADR-0031)* | ADR-0028/0029 | Live |
| 14 | Feature Engineering *(Layer 2, ADR-0031)* | none yet | Not started |
| 15 | Automation Engineering *(Layer 3, ADR-0031)* | none yet | Not started |
| 16 | Suite Quality Governance *(Layer 4, ADR-0031)* | none yet | Not started |
| 17 | Test Execution *(Layer 5, ADR-0031)* | none yet | Not started |
| 18 | Failure Intelligence & Self-Healing *(Layer 6, ADR-0031)* | none yet | Not started |
| 19 | Governance Dashboard *(Layer 7, ADR-0031)* | none yet | Not started, and structurally different — see D5 |

Stages 1–13 exist and run today, synchronously, in this exact order, inside the current CLI. Stages 14–19 are reserved slots — this ADR gives them a place in the state model; it does not build them.

### Resume semantics

- **Resume from the first non-`SUCCEEDED` stage.** A run that failed at stage 9 and is re-invoked with the same `run_id` re-executes from stage 9 onward, skipping 1–8 (already `SUCCEEDED`), rather than restarting from stage 1.
- **Each stage declares its inputs as artifact paths produced by prior stages**, not as in-memory objects handed off within one process — this is what makes resuming a genuinely separate process possible (D2).
- **Stages must be idempotent.** Re-running a stage against the same inputs must produce the same output artifact(s) (or safely detect and skip re-production), never a second, conflicting copy.

### Lockfile

A lockfile at the run root prevents two processes from operating on the same `run_id` concurrently. A process that finds a live lock held by another process refuses to proceed rather than racing it.

### No database

Filesystem only, at this stage — `run_state.json` is a file, not a table. This is consistent with, and does not reopen, the "no database yet" position `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.4 and Open Question 12 already recorded.

## D1 — Why a new file alongside the manifest, not a manifest extension

`docs/adr/0017-quality-governance-framework.md` §D31 froze `manifest.json`'s charter permanently: it "owns exactly six kinds of information... and nothing else," and a manifest field is legitimate "only if it answers 'what package is this?' or 'what artifacts does it contain?'" A stage's `RUNNING`/`FAILED`/`SKIPPED` status answers neither question — it is runtime *progress*, not package *identity* or *contents*. Adding stage state to `manifest.json` would repeat exactly the mistake CAP-080D.1 already found and fixed once (the `qualityGovernanceDecision` field). `run_state.json` is therefore a distinct file with its own, different charter: progress, not indexing.

## D2 — Why stage inputs must be artifact paths, not in-process objects

Today's phase functions (`run_engineering_pipeline`, `run_validation_phase`, etc., per `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.1) pass results as Python objects within one process's memory. That is precisely what makes resuming impossible — a second process invoked later has none of that memory. Requiring every stage to declare its inputs as artifact paths (files the prior stage already wrote) means a resumed process can reconstruct exactly what a continuous process would have had, by reading from disk, regardless of which process or how much later it runs.

## D3 — Why `--execution-name` survives as a label, not a path

The human-chosen name is useful — `demo-readiness-20260720` is far more legible than a platform-minted `run_id` — but using it as the directory path is what makes today's naming "ad hoc" (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.4): two runs could collide on the same name, and nothing enforces uniqueness. Recording it as a label inside `run_state.json`, keyed by the platform-assigned `run_id` path, keeps the legibility without losing the uniqueness guarantee a resumable, lockable run identity requires.

## D4 — Why a lockfile, given there is no database

A database would typically arbitrate concurrent access with a transaction; filesystem-only persistence (the deliberate, unrevisited choice re-confirmed in D-none/§Runtime status) has no equivalent. A lockfile is the minimal mechanism that prevents the one failure mode resumability introduces: two processes resuming the same `run_id` at once, each partially overwriting the other's stage outputs. It is scoped narrowly to that problem, not a general-purpose coordination mechanism.

## D5 — Governance Dashboard's stage slot is structurally different, and this ADR does not resolve that

Stages 1–18 each produce an artifact consumed by a later stage or by a human reading that one run's output. Governance Dashboard (Layer 7, stage 19) is described in ADR-0031 as rendering **leadership-facing insight across runs** — by nature a cross-run, always-on view, not a per-run production step with a `SUCCEEDED`/`FAILED` outcome of its own. Reserving it a slot in this table is consistent with the instruction to cover all seven layers, but this ADR does not resolve whether Layer 7 is genuinely a per-run pipeline stage at all, or whether it is better modeled as a separate, continuously-running service that reads completed runs' `run_state.json`/`manifest.json` files rather than participating in any one run's stage sequence. This is recorded as an open question in `docs/architecture/architecture-baseline-v2.md`, not guessed at here.

---

## TBD — deferred to implementation

- The exact `run_id` generation scheme (format, timestamp-derived vs. random vs. content-addressed).
- `run_state.json`'s exact field list and schema (this ADR locks its charter — stage statuses, the human label, per-stage input artifact paths — not its serialization).
- The lockfile's exact mechanism (a `.lock` file with a PID, an OS-level advisory lock, etc.).
- Whether Governance Dashboard participates in the stage sequence at all (D5).

## Recommendations (permanent)

1. **`manifest.json`'s charter (ADR-0017 §D31) is never widened to include stage progress.** `run_state.json` is the sole owner of stage state, permanently.
2. **Every future stage (14–19, once built) declares its inputs as artifact paths, not in-process handoffs**, from the day it is first implemented — not retrofitted later.
3. **Idempotency is a mandatory property of every stage, present and future**, verified by test before a stage is considered done.

## Ownership, scope, and governance

- **Owns:** the run/stage state model's existence, `run_id`'s role as the canonical path identifier, the stage list and its statuses, resume semantics, and the lockfile's purpose.
- **Does not own:** `manifest.json` or any existing Execution Package artifact (unchanged, owned by CAP-020/022 and ADR-0017 §D31); any individual stage's own internal architecture (owned by that stage's governing ADR); Layer 7's ultimate resolution as a stage or a service (D5, open).
- **Governance:** Accepted as an architecture freeze. Implementation is authorized under ADR-0032 carve-out 2.
