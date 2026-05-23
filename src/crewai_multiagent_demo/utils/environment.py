from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from crewai_multiagent_demo.utils.paths import DEFAULT_CACHE_DIR, DEFAULT_ENV_FILE


def configure_runtime_environment(project_root: Path | None = None) -> None:
    """Keep CrewAI and telemetry runtime files inside the project."""
    root_cache = (project_root / ".cache") if project_root else DEFAULT_CACHE_DIR
    crewai_storage = root_cache / "crewai"
    local_app_data = root_cache / "localappdata"

    os.environ.setdefault("CREWAI_STORAGE_DIR", str(crewai_storage))
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    os.environ.setdefault("CREWAI_TESTING", "true")
    os.environ["LOCALAPPDATA"] = str(local_app_data)


def load_project_env(env_file: Path | None = None) -> None:
    configure_runtime_environment()
    _configure_utf8_stdio()
    load_dotenv(env_file or DEFAULT_ENV_FILE)


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def has_api_key() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"))


def require_api_key() -> None:
    if not has_api_key():
        raise RuntimeError(
            "缺少 API key。请复制 .env.template 为 .env，并填写 DEEPSEEK_API_KEY。"
        )
