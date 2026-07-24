# ADR-0039 — Execution Backend and CI/CD

- **Status:** **PROPOSED — NOT ACCEPTED.** No component may be built against this ADR until it is ratified. This status line, and this warning, are load-bearing: unlike ADR-0031 through ADR-0038 in this batch, this decision is not locked.
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none. Evidentiary basis: `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.7 (no CI/CD configuration exists anywhere in the repository — re-confirmed for this ADR: no `.github/`, `.gitlab-ci.yml`, or `Jenkinsfile` found) and §2.2 (the real SonarQube findings the platform's own connector already ingests).
- **Depends on:** ADR-0036 (Run and Stage State Model — `run_state.json` is what this ADR's asynchronous stage must remain subordinate to, D2); ADR-0037 (Generated Test Suite Target and SUT Binding — Jenkins would execute the suite this ADR governs); ADR-0031 (Layer 5 Test Execution, Layer 4 Suite Quality Governance — the two layers this ADR's execution backend serves).
- **Runtime status:** Not applicable. Proposed architecture only. No CI configuration, no `Jenkinsfile`, no `ExecutionBackend` interface, and no code of any kind exists as a result of this ADR.

## Problem

`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.7 established, and this ADR re-confirms directly (no `.github/`, `.gitlab-ci.yml`, or `Jenkinsfile` anywhere in the tracked repository): there is no CI/CD for the platform itself today, and — because Layer 5 (Test Execution) does not exist — no execution backend for running the generated Java suite either. These are two different problems that a single tool choice risks conflating: verifying the platform's own Python code on every change, versus actually running a generated Cucumber suite against a system under test. Choosing a CI/CD tool without separating those two roles risks designing Layer 5 around whatever a CI tool makes easy, rather than around what Layer 5 actually needs.

## Decision (Proposed)

**Jenkins is selected as the CI/CD tool.**

Jenkins is proposed to serve **two distinct roles, which must not be conflated**:

1. **CI for the platform itself** — running `ruff`, `mypy`, and `pytest` (the existing `make check` target, `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §1.4) against every change to this repository's own Python code.
2. **An execution backend for Layer 5** — running the generated Java suite — and for the SonarQube scan of generated code that Layer 4 (Suite Quality Governance) consumes.

**Proposed direction:** the platform orchestrates; Jenkins sits **behind an `ExecutionBackend` interface** as one implementation of it, never invoked directly by Layer 5's own logic. **A local Maven/Gradle runner is the default implementation**, so Layer 5 is buildable and testable without Jenkins available — Jenkins is an optional, swappable backend, not a hard dependency of Layer 5's own architecture.

## D1 — Why the two roles must not be conflated

Role 1 (platform CI) is synchronous from the point of view of a pull request: a developer expects `ruff`/`mypy`/`pytest` results before merging, on the order of minutes, and the trigger/consumer are both this repository's own contribution workflow. Role 2 (execution backend) is Layer 5's own runtime dependency, triggered by a pipeline run rather than a pull request, and — per D2 — has fundamentally different timing characteristics. Treating them as one undifferentiated "Jenkins" concern risks Layer 5's architecture inheriting assumptions (like "results are available synchronously within the same request") that only hold for role 1.

## D2 — The open problem this ADR flags for Layer 5's LLD, and does not resolve

A Jenkins-delegated execution is **asynchronous**: trigger a build, poll for completion, collect results — there is no single synchronous call that returns a result the way every existing Layer 1 phase function does today (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §3.1). This makes Layer 5 **the first stage in the entire pipeline that cannot be a synchronous call** under ADR-0036's stage model, which was designed against Layer 1's exclusively synchronous phases. ADR-0036 does not itself resolve this — its resume/idempotency properties (input artifacts, `SUCCEEDED`/`FAILED`/`RUNNING` status) are compatible with an asynchronous stage in principle (a stage can sit in `RUNNING` across multiple poll cycles), but the exact mechanism — how a `RUNNING` Layer 5 stage is polled, resumed if the orchestrating process restarts mid-poll, and reconciled with a Jenkins build that completed while nothing was watching it — is explicitly **left to Layer 5's own future architecture-freeze ADR** to resolve, not decided here.

**`run_state.json` (ADR-0036) remains authoritative over Jenkins build history.** Jenkins's own build log and history are a detail of one `ExecutionBackend` implementation; the platform's own record of what stage 17 (Test Execution) did, for a given `run_id`, is `run_state.json`, never a Jenkins URL a reader would have to separately trust or archive.

## D3 — Why an interface, not a direct dependency

Committing Layer 5's own logic to calling Jenkins directly would make every Layer 5 test — and every developer running Layer 5 locally without Jenkins available — dependent on a Jenkins instance existing and being reachable. An `ExecutionBackend` interface, with a local Maven/Gradle runner as the default implementation, means Layer 5's own architecture and tests can be built and verified without Jenkins, and Jenkins becomes an operational choice for how a given deployment executes the suite, not an architectural dependency of Layer 5 itself.

## Recommendations (Proposed — binding only once Accepted)

1. **No component is built against this ADR while it remains Proposed.** This includes Layer 5's own architecture-freeze ADR, which must either wait for this ADR's ratification or explicitly treat the execution-backend question as its own open item.
2. **The two Jenkins roles (platform CI, execution backend) are configured, documented, and reasoned about separately**, even if they end up on the same Jenkins instance operationally.
3. **`ExecutionBackend` is an interface from day one of implementation, never retrofitted after a direct Jenkins dependency is already built.**
4. **The asynchronous execution problem (D2) is Layer 5's own architecture-freeze ADR's responsibility to resolve** — this ADR names the problem; it does not solve it.

## Ownership, scope, and governance

- **Owns (once Accepted):** the CI/CD tool selection and the two-role separation.
- **Does not own:** the `ExecutionBackend` interface's exact shape (deferred to Layer 5's own architecture); the asynchronous stage-execution mechanism (D2, explicitly open); `run_state.json`'s own schema (owned by ADR-0036).
- **Governance:** **Proposed.** Becomes Accepted only through the same ratification process ADR-0032's freeze-lifting procedure describes — explicit Architecture Review Board approval — not by default or by a future ADR silently building against it.
