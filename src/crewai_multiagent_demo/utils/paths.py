from __future__ import annotations

import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    RESOURCE_ROOT = PROJECT_ROOT
DEFAULT_CONFIG_DIR = RESOURCE_ROOT / "config"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_CACHE_DIR = PROJECT_ROOT / ".cache"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def resolve_project_path(path: str | Path | None, default: Path) -> Path:
    if path is None:
        return default
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()
