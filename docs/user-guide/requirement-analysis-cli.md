# Requirement Analysis CLI

The official command-line interface for the Autonomous Test Engineering Platform.

`scripts/run_requirement_analysis.py`

---

## Overview

The Requirement Analysis CLI is a **subcommand-based orchestration tool** (in the
style of `git`, `docker`, and `kubectl`) that drives the platform's AI pipeline
end-to-end and captures a reproducible execution package.

It is **architecture-neutral** and contains **no business logic** — every
analytical decision happens inside the platform layers the CLI calls. The CLI
only sequences the existing components, captures their outputs, and writes an
execution package.

| Property            | Value |
| ------------------- | ----- |
| Entry point         | `python scripts/run_requirement_analysis.py` |
| Style               | Subcommand-based (argparse subparsers) |
| Contains business logic | No — orchestration only |
| Live AI provider    | Gemini (others pluggable without CLI changes) |

---

## Architecture

The execution flow is unchanged from the platform pipeline — **no layer is
bypassed and the provider is never called directly:**

```text
   Connectors
       ↓
   Mappers
       ↓
   Consolidation Engine
       ↓
   RequirementAnalysisService
       ↓
   RequirementPromptBuilder → PromptRequest → LLMRequest
       ↓
   LLM Provider  →  Google Gemini  →  LLMResponse
       ↓
   AnalysisResult
```

The CLI itself is a **thin orchestration layer**: parse arguments → create a
`PlatformContext` → execute the requested subcommand → display progress. It holds
no file-format knowledge and constructs no platform component directly.

```text
         Requirement Analysis CLI  (thin orchestration)
           │ construct        │ introspect       │ package
           ▼                  ▼                  ▼
   PlatformContext     PlatformCapabilities   Execution package
   (dependency          (version cmd:          (ExecutionWriter,
    factory)             metadata + host)       History, builders)
```

---

## Internal Architecture

The CLI delegates to the platform and execution packages so it can stay thin and
stable.

### PlatformContext (`requirement_intelligence.platform`)

A pure **dependency factory**. The CLI asks it for components instead of
instantiating them itself. It contains no business logic.

| Factory method | Returns |
| -------------- | ------- |
| `create_connector_registry()` | Connector + Mapper orchestrator |
| `create_consolidation_engine()` | Consolidation engine |
| `create_prompt_builder()` | Requirement prompt builder |
| `create_provider(name, model)` | An `LLMProvider` (via the platform factory) |
| `create_analysis_configuration(version)` | Execution configuration |
| `create_requirement_analysis_service(...)` | The analysis service |

Platform metadata (versions, the architecture capability catalogue, the provider
catalogue, and the CLI command list) lives in
`requirement_intelligence.platform.platform_metadata` — a single source of truth.

### PlatformCapabilities (`requirement_intelligence.platform`)

`PlatformCapabilities` is the **platform introspection model**. The `version`
command reads everything from it instead of touching metadata constants directly.
It contains no business logic.

| Method | Returns |
| ------ | ------- |
| `platform_identity()` | Name, architecture, execution mode |
| `platform_versions()` | Platform/CLI/Prompt/Reasoning/Execution-Package/Manifest-Schema versions |
| `architecture_components()` / `implemented_components()` / `planned_components()` | The capability catalogue (all / available / planned) |
| `component_groups()` | Ordered `(group title, components)` — Core / AI / Execution / Future |
| `providers()` | The provider catalogue |
| `supported_commands()` | Registered CLI command names |
| `system_identity()` | Python version, OS, architecture, working directory |

### Execution package (`requirement_intelligence.execution`)

All execution-package file generation lives here, not in the CLI.

| Component | Responsibility |
| --------- | -------------- |
| `ExecutionWriter` | Writes every execution artifact (delegates to the builders). The CLI just calls `ExecutionWriter.write(target_dir, data)`. |
| `ExecutionHistory` | `latest/`, timestamped/named history directories, creation, and copying. |
| `ManifestBuilder` | `manifest.json` only. |
| `ExecutionSummaryBuilder` | `execution_summary.md` only. |
| `BaselineMetricsBuilder` | `baseline_metrics.md` only. |
| `ReviewBuilder` | `review.md` only. |

`ExecutionData` is the immutable input bundle the CLI passes to the writer.

---

## CLI Structure

```text
python scripts/run_requirement_analysis.py <subcommand> [options]
```

| Subcommand       | Purpose |
| ---------------- | ------- |
| `analyze`        | Execute a complete AI analysis (live, or `--dry-run`). |
| `health`         | Check every enabled source is reachable. Runs no pipeline stage. |
| `list-artifacts` | Run the engineering pipeline and list all ConsolidatedArtifacts. |
| `version`        | Platform introspection (metadata, capabilities, providers, system info). |
| `help`           | Detailed usage and examples. |

Built-in `-h` / `--help` is available on the tool and on every subcommand.

## Execution mode

One environment variable selects how **every** source is ingested. Sources are
never configured independently.

| `EXECUTION_MODE` | Behaviour |
| ---------------- | --------- |
| `FILE` (default) | Connectors read exported artifacts from `inputPath`. |
| `API`            | Connectors fetch live from JIRA, SonarQube, OWASP ZAP. |

An unset or empty value means `FILE`. Any other value is rejected at startup
with exit code `2`. Startup validation runs before any source is contacted and
names every missing configuration value.

---

## Supported Subcommands

### `analyze`

Executes one complete AI analysis.

| Option              | Default              | Description |
| ------------------- | -------------------- | ----------- |
| `--artifact-id <id>`| deterministic select | Analyse a specific ConsolidatedArtifact. If omitted, the largest artifact (by grouped count, tie-break by id) is chosen — fully reproducible. |
| `--provider <name>` | `gemini`             | LLM provider. Validated against supported providers (`gemini` today). Future providers plug in without CLI changes. |
| `--model <name>`    | provider env model   | Override the configured model. |
| `--output-dir <dir>`| `output/executions/` | Base directory for saved executions. |
| `--execution-name <n>` | off               | Store under `output/executions/<n>/` instead of a timestamp (implies `--save-execution`; never overwrites — appends `-1`, `-2`, …). |
| `--dry-run`         | off                  | Run through prompt generation only; do **not** call the provider. |
| `--save-execution`  | off                  | Keep a permanent, timestamped execution history copy. |
| `--verbose`         | off                  | Detailed progress output. |

### `version`

A platform introspection command. All data comes from `PlatformCapabilities`;
nothing is hardcoded in the CLI. Organised into grouped sections:

- **Platform Metadata** — Platform Identity (architecture, execution mode) and
  the version block: Platform, CLI, Prompt, Reasoning Contract, Execution Package,
  and **Manifest Schema** versions.
- **Core Platform** — Connector Registry, Connectors, Mappers, Consolidation Engine.
- **AI Platform** — Prompt Framework, LLM Framework, Gemini Provider, Requirement
  Analysis Service.
- **Execution Platform** — Execution Package, Requirement Analysis CLI.
- **Future Platform** — Feature Generator, Test Generator (`○`, planned).
- **Available Providers** — `✓ Gemini`, plus reserved providers (`○`).
- **Supported Commands** — the registered subcommands.
- **System Information** — Python version, OS, architecture, working directory
  (no sensitive information).

```bash
python scripts/run_requirement_analysis.py version
```

### `list-artifacts`

Runs the engineering pipeline only and displays every ConsolidatedArtifact
(Consolidated ID, Business Area, Module, Risk Level, and functional/security/
quality counts). Does **not** invoke the LLM and writes nothing.

### `health`

Probes every enabled source and reports `READY`, `MISCONFIGURED`, or
`UNREACHABLE`. Exercises the connector layer only — no consolidation, no LLM
call, no validation, no CP1, no execution package. Exit code is `0` only when
every source is `READY`, so the command works as a deployment gate.

```bash
python scripts/run_requirement_analysis.py health
EXECUTION_MODE=API python scripts/run_requirement_analysis.py health --verbose
```

### `help`

Prints detailed usage with worked examples.

---

## `analyze` Examples

```bash
# Backward-compatible baseline run (live). Writes to output/latest/.
python scripts/run_requirement_analysis.py analyze

# Analyse a specific artifact and keep a permanent history entry.
python scripts/run_requirement_analysis.py analyze \
    --artifact-id cons-component-authentication --save-execution

# Override the model for a single run.
python scripts/run_requirement_analysis.py analyze --model gemini-2.5-flash

# Verbose live run, persisted to history.
python scripts/run_requirement_analysis.py analyze --save-execution --verbose

# Named execution — persisted under output/executions/prompt-v1.1/
python scripts/run_requirement_analysis.py analyze --execution-name prompt-v1.1
```

> **Prerequisite for live runs:** `GOOGLE_API_KEY` must be set (environment or a
> local, gitignored `.env`). See `docs/integrations/google-gemini.md`.

---

## `list-artifacts` Examples

```bash
# List every consolidated artifact discovered from the sample inputs.
python scripts/run_requirement_analysis.py list-artifacts

# With detailed pipeline progress.
python scripts/run_requirement_analysis.py list-artifacts --verbose
```

Example output (truncated):

```text
Consolidated Artifacts (23):

- cons-component-...-badloginpage-java
    Business Area : -
    Module        : Automation-POC:.../BadLoginPage.java
    Risk Level    : critical
    Functional    : 0
    Security      : 0
    Quality       : 71
```

---

## Dry Run

`--dry-run` exercises everything up to and including prompt generation, then
stops before any provider call:

```bash
python scripts/run_requirement_analysis.py analyze --dry-run --verbose
```

It still writes the deterministic, provider-independent artifacts:

- `consolidated_artifact.json`
- `prompt.txt`
- `llm_request.json`
- `manifest.json` (with `"executionMode": "dry-run"`, `"dryRun": true`)

No `GOOGLE_API_KEY` is required for a dry run.

---

## Execution History

Each successful `analyze` always refreshes:

```text
output/latest/        # always the most recent execution package
```

With `--save-execution`, a permanent, **never-overwritten** copy is also kept:

```text
output/executions/YYYY-MM-DD_HH-MM-SS/     # timestamped history
output/executions/<execution-name>/        # named history (--execution-name)
```

Directory selection is owned by `ExecutionHistory`:

- No persistence flag → write to `output/latest/` only.
- `--save-execution` → `output/executions/<timestamp>/` (suffix `_1`, `_2`, … on
  collision).
- `--execution-name <n>` → `output/executions/<n>/` (suffix `-1`, `-2`, … on
  collision); implies persistence.

`output/latest/` is always refreshed from the written execution. Copies are used
(not symbolic links) for maximum cross-platform compatibility, and no previous
execution is ever overwritten.

---

## Output Package

Every execution package contains a canonical `manifest.json` plus its artifacts.

| Artifact                    | Written on | Description |
| --------------------------- | ---------- | ----------- |
| `manifest.json`             | always     | Canonical entry point / index. |
| `consolidated_artifact.json`| always     | The exact ConsolidatedArtifact analysed. |
| `prompt.txt`                | always     | System + User prompt submitted to the provider. |
| `llm_request.json`          | always     | Serialised LLMRequest. |
| `analysis_result.json`      | live only  | Serialised AnalysisResult. |
| `raw_llm_response.json`     | live only  | Raw provider response (unmodified). |
| `execution_summary.md`      | live only  | Human-readable summary. |
| `baseline_metrics.md`       | live only  | Metrics table. |
| `review.md`                 | live only  | Qualitative review scaffold. |

`manifest.json` is independently versioned and self-describing. Fields include:

- **Versioning:** `manifestSchemaVersion`, `platformVersion`, `baselineVersion`,
  `executionPackageVersion`, and per-component versions
  (`connectorRegistryVersion`, `mapperVersion`, `consolidationEngineVersion`,
  `promptFrameworkVersion`, `llmFrameworkVersion`, `analysisServiceVersion`,
  `executionWriterVersion`, `platformCapabilitiesVersion`).
- **Execution:** `subcommand`, `executionMode`, `dryRun`, `executionName`,
  `executionTimestamp`, `executionCompletedTimestamp`, `analysisId`,
  `executionId`, `provider`, `model`, `promptVersion`,
  `reasoningContractVersion`, `selectedArtifactId`, `executionDurationMs`,
  `executionSucceeded`.
- **Integrity:** `promptSha256`, `responseSha256`, `commandLineArguments`, and
  `generatedArtifacts` (name + bytes + sha256 per file).

> **Version semantics**
> - **Platform Version** — the platform release as a whole.
> - **Execution Package Version** — the execution-artifact generation contract.
> - **Manifest Schema Version** — the JSON contract of `manifest.json`. Future
>   manifest changes only require incrementing `MANIFEST_SCHEMA_VERSION`.

### Engineering Metrics (live `baseline_metrics.md`)

A dedicated **Engineering Metrics** section is computed *only* from the platform
pipeline (it never inspects AI output): Source Artifacts Processed, Consolidated
Artifacts Produced, Functional/Security/Quality Artifact Counts of the selected
artifact, Selected Consolidated Artifact, Selected Artifact Rank, Largest /
Smallest Consolidation Group, and Average Artifacts Per Group. The existing **AI
Metrics** section is unchanged.

### Execution Package Identity (live `execution_summary.md` and `review.md`)

Each live package carries a human-readable identity block: an **Execution Package
Id** of the form `EP-YYYYMMDD-HHMMSS-XXXXXXXX` (where `XXXXXXXX` is the first
eight characters of the execution id), alongside Platform / Execution Package /
Manifest Schema / Prompt / Reasoning Contract versions and the Provider and
Model. The identifier is for human traceability only and does **not** replace
`executionId`.

The `promptSha256` / `responseSha256` hashes enable reproducibility checks and
baseline comparison across prompt and reasoning versions.

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
| ------- | ------------ | ---------- |
| `GOOGLE_API_KEY is not set` | No key in environment/`.env` | Export the key, add it to `.env`, or use `--dry-run`. |
| `Provider '<x>' is not supported` | Unimplemented `--provider` | Use `gemini` (the only provider implemented today). |
| `No consolidated artifact found with id '<x>'` | Bad `--artifact-id` | Run `list-artifacts` to see valid ids. |
| `Analysis failed: ... RESOURCE_EXHAUSTED` | Provider quota/rate limit | Retry later, switch model with `--model`, or check billing. |
| `google-genai package is not installed` | SDK missing | `pip install -r requirements.txt`. |
| No `output/latest/` after run | Run failed before writing | Re-run with `--verbose` and inspect the error. |

---

## Future Subcommands

The CLI is designed so new capabilities require only **one handler + one
subparser registration** — no architectural change. Reserved/anticipated:

| Subcommand          | Intent |
| ------------------- | ------ |
| `generate-features` | Generate feature specifications. |
| `generate-tests`    | Generate executable tests. |
| `compare-providers` | Compare output across providers. |
| `compare-prompts`   | Compare output across prompt versions. |
| `export` / `report` | Export or report on execution packages. |

To add one: implement `handle_<name>(args)`, register it in `build_parser()`
with `set_defaults(func=handle_<name>)`. The pipeline, manifest, and history
machinery are reused unchanged.
