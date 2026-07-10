# Architecture

This project is a local CrewAI multi-agent desktop/CLI application. Runtime data,
dependency caches, build artifacts, and outputs are intended to stay inside the
project directory.

## Runtime Flow

1. CLI or GUI loads `.env` through `utils.environment`.
2. Config is read from `config/agents.json` and `config/tasks.json`.
3. `config.validation` validates enabled agents, enabled tasks, dependencies,
   missing references, disabled references, and dependency cycles.
4. `core.runner.run_workflow` resolves the model, checks the provider-specific
   API key, builds the CrewAI crew, runs it, and archives outputs.
5. Successful runs write reports, task outputs, metadata, and events.
6. Failed runs also write a failure report, metadata, and events for debugging.

## Main Packages

- `config/`: JSON parsing, schema normalization, and validation.
- `core/`: workflow ordering, CrewAI construction, execution, events, and output files.
- `domain/`: small dataclasses shared across layers.
- `gui/`: desktop bridge, history/config services, legacy widgets, and the Qt WebEngine host.
- `frontend/`: React + TypeScript interface, motion system, local QWebChannel adapter, and browser-facing tests.
- `llm/`: model aliases and provider-specific model names.
- `utils/`: path and environment setup.

## GUI Boundaries

- `src/web_gui_app.py` is the desktop entrypoint. It creates the Qt window and
  starts the local WebEngine page; `src/gui_app.py` remains the legacy Qt
  Widgets entrypoint while the existing working-tree redesign is preserved.
- `gui/bridge.py` is the only browser-facing Python API. It owns the worker,
  config/history operations, path validation, and QWebChannel JSON contracts.
- `gui/web_host.py` owns local-resource loading, QWebChannel registration and
  navigation restrictions. The embedded page never receives API keys or local
  paths.
- `frontend/` owns presentation, responsive layout and animations. It may only
  call the typed bridge adapter; it must not reproduce business validation.
- `gui/services.py` remains the pure-Python boundary for configuration and
  history reads/writes.

Keep business rules out of React components and Qt page objects. Logic that can
be tested without a rendered WebEngine page belongs in `services.py`,
`bridge.py`, `state.py`, or `core/`.

## Extension Points

- Add or change model aliases in `llm/model_registry.py`.
- Add new config rules in `config/validation.py`.
- Add output formats in `core/outputs.py`.
- Add new GUI screens in `gui/pages.py` first; move complex non-visual behavior
  into a service module before wiring it to widgets.

## Verification

Run these before shipping changes:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe .\src\main.py validate
.\.venv\Scripts\python.exe .\src\gui_app.py --smoke-test
.\.venv\Scripts\python.exe .\src\web_gui_app.py --smoke-test
cd frontend; pnpm run build; pnpm run test
```
