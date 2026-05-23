from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"
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
