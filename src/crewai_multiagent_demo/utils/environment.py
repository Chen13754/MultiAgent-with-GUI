from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from crewai_multiagent_demo.utils.paths import DEFAULT_CACHE_DIR, DEFAULT_ENV_FILE, PROJECT_ROOT


LAST_ENV_FILE: Path | None = None


def configure_runtime_environment(project_root: Path | None = None) -> None:
    """Keep CrewAI and telemetry runtime files inside the project."""
    env_project_root = os.getenv("MULTIAGENT_PROJECT_ROOT")
    if project_root is None and env_project_root:
        project_root = Path(env_project_root)
    root_cache = (project_root / ".cache") if project_root else DEFAULT_CACHE_DIR
    crewai_storage = root_cache / "crewai"
    local_app_data = root_cache / "localappdata"

    os.environ.setdefault("CREWAI_STORAGE_DIR", str(crewai_storage))
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    os.environ.setdefault("CREWAI_TESTING", "true")
    os.environ["LOCALAPPDATA"] = str(local_app_data)


def candidate_env_files(env_file: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    explicit = os.getenv("MULTIAGENT_ENV_FILE")
    project_root = os.getenv("MULTIAGENT_PROJECT_ROOT")
    for value in (
        env_file,
        Path(explicit) if explicit else None,
        Path.cwd() / ".env",
        Path(project_root) / ".env" if project_root else None,
        PROJECT_ROOT / ".env",
        DEFAULT_ENV_FILE,
    ):
        if value is None:
            continue
        path = Path(value).expanduser()
        if path not in candidates:
            candidates.append(path)
    return candidates


def load_project_env(env_file: Path | None = None) -> Path | None:
    global LAST_ENV_FILE
    configure_runtime_environment()
    _configure_utf8_stdio()
    for candidate in candidate_env_files(env_file):
        if candidate.exists():
            load_dotenv(candidate, override=True)
            LAST_ENV_FILE = candidate
            return candidate
    LAST_ENV_FILE = None
    return None


def loaded_env_file() -> Path | None:
    return LAST_ENV_FILE


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
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
    if crewai_model is None:
        if has_api_key():
            return
        required_names = ("DEEPSEEK_API_KEY", "OPENAI_API_KEY")
    else:
        if has_api_key_for_model(crewai_model):
            return
        required_names = api_key_env_names_for_model(crewai_model)
    raise RuntimeError(f"Missing API key. Please set one of: {', '.join(required_names)}.")
