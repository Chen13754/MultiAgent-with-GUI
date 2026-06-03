from __future__ import annotations

import sys
from pathlib import Path


def _frozen_project_root(executable: Path) -> Path:
    exe_dir = executable.resolve().parent
    if exe_dir.name == "MultiagentStudio" and exe_dir.parent.name == "dist":
        return exe_dir.parents[1]
    return exe_dir


if getattr(sys, "frozen", False):
    PROJECT_ROOT = _frozen_project_root(Path(sys.executable))
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
