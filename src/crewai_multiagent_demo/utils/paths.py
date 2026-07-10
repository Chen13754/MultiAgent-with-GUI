from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir, user_data_dir


def _frozen_project_root(executable: Path) -> Path:
    exe_dir = executable.resolve().parent
    if exe_dir.name == "MultiagentStudio" and exe_dir.parent.name == "dist":
        return exe_dir.parents[1]
    return exe_dir


APP_NAME = "MultiagentStudio"
IS_FROZEN = bool(getattr(sys, "frozen", False))

if IS_FROZEN:
    PROJECT_ROOT = _frozen_project_root(Path(sys.executable))
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    RESOURCE_ROOT = PROJECT_ROOT
LEGACY_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else PROJECT_ROOT
BUNDLED_CONFIG_DIR = RESOURCE_ROOT / "config"

if IS_FROZEN:
    DEFAULT_CONFIG_DIR = Path(user_config_dir(APP_NAME, appauthor=False)) / "config"
    DEFAULT_OUTPUT_DIR = Path(user_data_dir(APP_NAME, appauthor=False)) / "outputs"
    DEFAULT_CACHE_DIR = Path(user_cache_dir(APP_NAME, appauthor=False))
    DEFAULT_ENV_FILE = DEFAULT_CONFIG_DIR.parent / ".env"
else:
    DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"
    DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
    DEFAULT_CACHE_DIR = PROJECT_ROOT / ".cache"
    DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class GuiWorkspace:
    config_dir: Path
    output_dir: Path
    cache_dir: Path
    legacy_output_dir: Path | None


def ensure_gui_workspace() -> GuiWorkspace:
    """Create the writable desktop workspace and seed it with bundled defaults.

    Source runs deliberately retain the repository-local layout. Frozen desktop
    builds use operating-system application directories, while importing a
    sibling legacy configuration once so existing Windows users keep their setup.
    """

    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if IS_FROZEN:
        legacy_config = LEGACY_ROOT / "config"
        source_config = legacy_config if legacy_config.exists() else BUNDLED_CONFIG_DIR
        for name in ("agents.json", "tasks.json"):
            destination = DEFAULT_CONFIG_DIR / name
            source = source_config / name
            if not destination.exists() and source.exists():
                shutil.copy2(source, destination)

    legacy_output = LEGACY_ROOT / "outputs" if IS_FROZEN else None
    if legacy_output == DEFAULT_OUTPUT_DIR or not legacy_output or not legacy_output.exists():
        legacy_output = None
    return GuiWorkspace(
        config_dir=DEFAULT_CONFIG_DIR,
        output_dir=DEFAULT_OUTPUT_DIR,
        cache_dir=DEFAULT_CACHE_DIR,
        legacy_output_dir=legacy_output,
    )


def resolve_project_path(path: str | Path | None, default: Path) -> Path:
    if path is None:
        return default
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()
