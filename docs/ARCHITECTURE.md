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
- `gui/`: desktop UI split into page construction, widgets, state helpers, and services.
- `llm/`: model aliases and provider-specific model names.
- `utils/`: path and environment setup.

## GUI Boundaries

- `src/gui_app.py` owns the main window, run state, event handling, rendering,
  and user-facing message boxes.
- `gui/pages.py` owns Qt page construction and table widget helpers.
- `gui/services.py` owns config editor reads/writes, validation text, history
  discovery, and history file reads.
- `gui/widgets.py` owns custom animated/polished widgets.

Keep business rules out of page construction code. If logic can be tested
without a `QApplication`, put it in `services.py`, `state.py`, or `core/`.

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
```
