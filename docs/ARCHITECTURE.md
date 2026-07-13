# Architecture

Multiagent Studio is a local CrewAI desktop/CLI application. The supported GUI stack is React, QWebChannel, and PySide6 Qt WebEngine; the former Qt Widgets implementation has been retired.

## Runtime flow

1. The entrypoint creates a writable application workspace and seeds immutable defaults.
2. `.env` is loaded without overriding injected environment variables; storage paths are normalized to writable absolute paths.
3. `ConfigLoader` reads versioned `workflow.json`, or atomically migrates the legacy two-file configuration with backups.
4. The GUI creates an immutable `RunRequest` carrying run ID, topic, model, the validated `AppConfig` snapshot, its revision, config/output directories, timeouts, and retry limits.
5. `WorkflowProcessWorker` starts an isolated child process. The GUI can request cancellation; after the grace period it terminates and then kills the child if required.
6. `core.runner` validates, executes, and persists the state machine and outputs. Every failure path attempts to leave a diagnostic manifest without masking the original error.
7. History reads `run.json` as its authoritative source, with a legacy Markdown fallback only for old runs.

## Package boundaries

- `config/`: versioned loading/migration, normalization, validation, and atomic saves.
- `contracts/`: the JSON Schema that defines browser/Python protocol data.
- `core/`: workflow ordering, CrewAI construction, execution, events, and artifacts.
- `domain/`: immutable request/result and agent/task dataclasses shared across layers.
- `gui/run_process.py`: process lifecycle, cancellation, timeout, and crash cleanup.
- `gui/bridge.py`: narrow QWebChannel adapter and protocol version boundary.
- `gui/services.py`: configuration and history services that do not require rendering.
- `gui/web_host.py`: local WebEngine loading, channel registration, and navigation policy.
- `frontend/`: React presentation, generated contracts, runtime validation, and dynamic DAG rendering.
- `llm/`: model aliases and provider specifications.
- `utils/`: application paths, environment setup, atomic files, logging, and diagnostics.

Business rules belong in `config/`, `core/`, `domain/`, or testable services. React must not duplicate configuration validation, infer reports from task positions, access secrets, or fabricate production backend responses.

## Persistence contracts

- `workflow.json` (schema 2) and `run.json` carry `schema_version`; schema 1 remains readable for legacy migration.
- `workflow.json.graph.positions` stores presentation layout only. Task topology remains authoritative in `tasks[*].context_task_ids`.
- `run.json.config_revision` records the exact configuration revision accepted for that run; a child process never re-reads a newer UI draft.
- Configuration, event lists, and manifests use temporary files plus atomic replacement.
- A run directory name combines UTC time and a UUID; creation is atomic and safe under concurrent starts.
- `artifact_role` selects full and concise reports independently of task IDs.
- Events include both `run_id` and `task_id` so parallel or skipped tasks remain identifiable.
- Diagnostics exclude `.env` and API keys and include bounded logs and recent manifests.

## Desktop protocol

The QWebChannel bootstrap response uses protocol version 2. TypeScript contracts are generated from `contracts/studio.schema.json`; bootstrap snapshots are checked for the required graph, revision, and task-state fields at runtime. If a production page cannot reach QWebChannel or receives an incompatible payload, it shows a fatal backend error; `MockBridge` is compiled for development mode only.

The host performs a real `studio.bootstrap()` call during smoke testing and verifies the protocol marker. A page rendering successfully is not sufficient evidence of backend connectivity.

## Extension rules

- New tasks and dependency edges: change `workflow.json`; the GUI graph is data-driven.
- New persisted fields: version the JSON Schema and provide a migration before changing readers.
- New bridge methods: add schema, generated types, runtime validation, Python implementation, and bridge tests together.
- New model/provider: add a `ProviderSpec` and `ModelSpec`; do not hard-code provider environment logic in the runner.
- Parallel execution: preserve `run_id`/`task_id` event identity and replace sequential callback assumptions before enabling it.
- New memory/knowledge features: prohibited while the ChromaDB security exception is active; first remove the vulnerable dependency condition and add threat-model tests.

## Release boundary

The wheel is the advanced-user CLI channel and includes seeded default configuration. The GUI is distributed only through platform desktop bundles. Release jobs must pass Python/TypeScript tests, coverage, lint, type checks, contract drift checks, dependency audit, source and packaged smoke tests, then emit version metadata, checksum, and SBOM.

Windows signing and macOS signing/notarization require release credentials outside the repository. Unsigned artifacts are development builds and must not be described as production releases.

Tagged releases require these GitHub Actions secrets:

- Windows: `WINDOWS_SIGN_CERTIFICATE_BASE64` and `WINDOWS_SIGN_CERTIFICATE_PASSWORD`.
- macOS: `MACOS_SIGN_CERTIFICATE_BASE64`, `MACOS_SIGN_CERTIFICATE_PASSWORD`, `MACOS_SIGN_IDENTITY`, `MACOS_NOTARY_APPLE_ID`, `MACOS_NOTARY_TEAM_ID`, and `MACOS_NOTARY_APP_PASSWORD`.

The build signs before creating the final archive. Tagged jobs verify the Windows Authenticode signature or the macOS code signature and notarization staple. Missing credentials are a hard failure. Packaged provider E2E is performed against a loopback-only OpenAI-compatible fake service. After all platform bundles pass, one controlled real-provider canary uses the `DEEPSEEK_CANARY_API_KEY` secret; the release is published only if it succeeds.
