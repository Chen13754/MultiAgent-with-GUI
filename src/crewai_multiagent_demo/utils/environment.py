from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from crewai_multiagent_demo.utils.paths import (
    APP_HOME,
    DEFAULT_CACHE_DIR,
    DEFAULT_ENV_FILE,
    IS_FROZEN,
    LEGACY_ROOT,
    PROJECT_ROOT,
)

LAST_ENV_FILE: Path | None = None


def _resolve_runtime_path(value: str | None, default: Path, *, base: Path = PROJECT_ROOT) -> Path:
    if not value:
        return default.resolve()
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base / candidate).resolve()


def configure_runtime_environment(project_root: Path | None = None) -> None:
    """Keep CrewAI, telemetry, and temporary runtime files in a writable workspace."""

    env_project_root = os.getenv("MULTIAGENT_PROJECT_ROOT")
    if project_root is None and env_project_root:
        project_root = Path(env_project_root)
    root_cache = (project_root / ".cache") if project_root else DEFAULT_CACHE_DIR
    root_cache = root_cache.expanduser().resolve()
    crewai_storage = _resolve_runtime_path(
        os.getenv("CREWAI_STORAGE_DIR"),
        root_cache / "crewai",
        base=(project_root or APP_HOME).expanduser().resolve(),
    )
    local_app_data = root_cache / "localappdata"
    crewai_storage.mkdir(parents=True, exist_ok=True)
    local_app_data.mkdir(parents=True, exist_ok=True)

    # CrewAI 1.x expects CREWAI_STORAGE_DIR to be an absolute directory. Always
    # normalize after loading .env so appdirs cannot reinterpret a relative path.
    os.environ["CREWAI_STORAGE_DIR"] = str(crewai_storage)
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    os.environ.setdefault("CREWAI_TESTING", "true")
    os.environ.setdefault("LOCALAPPDATA", str(local_app_data))


def candidate_env_files(env_file: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    explicit = os.getenv("MULTIAGENT_ENV_FILE")
    project_root = os.getenv("MULTIAGENT_PROJECT_ROOT")
    values: list[Path | None] = [
        env_file,
        Path(explicit) if explicit else None,
        Path(project_root) / ".env" if project_root else None,
        DEFAULT_ENV_FILE,
    ]
    if not IS_FROZEN:
        values.extend((Path.cwd() / ".env", PROJECT_ROOT / ".env"))
    else:
        values.append(LEGACY_ROOT / ".env")

    for value in values:
        if value is None:
            continue
        path = Path(value).expanduser()
        if path not in candidates:
            candidates.append(path)
    return candidates


def load_project_env(env_file: Path | None = None) -> Path | None:
    global LAST_ENV_FILE
    _configure_utf8_stdio()
    loaded: Path | None = None
    for candidate in candidate_env_files(env_file):
        if candidate.exists():
            # Process/managed-environment secrets take precedence over a local
            # file. This also prevents a blank template value from clearing one.
            load_dotenv(candidate, override=False)
            loaded = candidate
            break
    LAST_ENV_FILE = loaded
    configure_runtime_environment()
    return loaded


def loaded_env_file() -> Path | None:
    return LAST_ENV_FILE


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream: Any = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def has_api_key() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"))


def api_key_env_names_for_model(crewai_model: str) -> tuple[str, ...]:
    if crewai_model.startswith("deepseek/"):
        return ("DEEPSEEK_API_KEY",)
    return ("DEEPSEEK_API_KEY", "OPENAI_API_KEY")


def has_api_key_for_model(crewai_model: str) -> bool:
    return any(os.getenv(name) for name in api_key_env_names_for_model(crewai_model))


def require_api_key(crewai_model: str | None = None) -> None:
    required_names: tuple[str, ...]
    if crewai_model is None:
        if has_api_key():
            return
        required_names = ("DEEPSEEK_API_KEY", "OPENAI_API_KEY")
    else:
        if has_api_key_for_model(crewai_model):
            return
        required_names = api_key_env_names_for_model(crewai_model)
    raise RuntimeError(f"Missing API key. Please set one of: {', '.join(required_names)}.")
