from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir, user_data_dir

APP_NAME = "MultiagentStudio"
IS_FROZEN = bool(getattr(sys, "frozen", False))
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PROJECT_ROOT = Path(__file__).resolve().parents[3]
IS_SOURCE_CHECKOUT = (SOURCE_PROJECT_ROOT / "pyproject.toml").exists()


def _frozen_project_root(executable: Path) -> Path:
    exe_dir = executable.resolve().parent
    if exe_dir.name == APP_NAME and exe_dir.parent.name == "dist":
        return exe_dir.parents[1]
    return exe_dir


def _packaged_config_dir() -> Path:
    return Path(str(files("crewai_multiagent_demo").joinpath("resources").joinpath("config")))


if IS_FROZEN:
    PROJECT_ROOT = _frozen_project_root(Path(sys.executable))
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()
elif IS_SOURCE_CHECKOUT:
    PROJECT_ROOT = SOURCE_PROJECT_ROOT
    RESOURCE_ROOT = PROJECT_ROOT
else:
    # Installed wheels are not source checkouts. Runtime data belongs in the
    # user's application directory, while immutable defaults stay in-package.
    PROJECT_ROOT = Path(user_data_dir(APP_NAME, appauthor=False)).resolve()
    RESOURCE_ROOT = PACKAGE_ROOT

LEGACY_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else PROJECT_ROOT
_resource_config = RESOURCE_ROOT / "config"
BUNDLED_CONFIG_DIR = (
    _resource_config if (_resource_config / "workflow.json").exists() else _packaged_config_dir()
)

_home_override = os.getenv("MULTIAGENT_HOME")
if _home_override:
    APP_HOME = Path(_home_override).expanduser().resolve()
    DEFAULT_CONFIG_DIR = APP_HOME / "config"
    DEFAULT_OUTPUT_DIR = APP_HOME / "outputs"
    DEFAULT_CACHE_DIR = APP_HOME / ".cache"
    DEFAULT_ENV_FILE = APP_HOME / ".env"
elif IS_SOURCE_CHECKOUT and not IS_FROZEN:
    APP_HOME = PROJECT_ROOT
    DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"
    DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
    DEFAULT_CACHE_DIR = PROJECT_ROOT / ".cache"
    DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
else:
    APP_HOME = Path(user_data_dir(APP_NAME, appauthor=False)).resolve()
    DEFAULT_CONFIG_DIR = Path(user_config_dir(APP_NAME, appauthor=False)) / "config"
    DEFAULT_OUTPUT_DIR = APP_HOME / "outputs"
    DEFAULT_CACHE_DIR = Path(user_cache_dir(APP_NAME, appauthor=False))
    DEFAULT_ENV_FILE = Path(user_config_dir(APP_NAME, appauthor=False)) / ".env"


@dataclass(frozen=True)
class GuiWorkspace:
    config_dir: Path
    output_dir: Path
    cache_dir: Path
    env_file: Path
    legacy_output_dir: Path | None


def _seed_default_config() -> None:
    source_config = BUNDLED_CONFIG_DIR
    if IS_FROZEN:
        legacy_config = LEGACY_ROOT / "config"
        if legacy_config.exists():
            source_config = legacy_config

    for name in ("workflow.json", "agents.json", "tasks.json"):
        destination = DEFAULT_CONFIG_DIR / name
        source = source_config / name
        if not destination.exists() and source.exists():
            shutil.copy2(source, destination)


def ensure_gui_workspace() -> GuiWorkspace:
    """Create writable runtime directories and seed immutable defaults."""

    try:
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _seed_default_config()
    except OSError as exc:
        raise RuntimeError(
            "无法创建 Multiagent Studio 工作目录。"
            f"请检查权限或设置 MULTIAGENT_HOME 指向可写目录。目标: {APP_HOME}"
        ) from exc

    legacy_output = LEGACY_ROOT / "outputs" if IS_FROZEN else None
    if legacy_output == DEFAULT_OUTPUT_DIR or not legacy_output or not legacy_output.exists():
        legacy_output = None
    return GuiWorkspace(
        config_dir=DEFAULT_CONFIG_DIR,
        output_dir=DEFAULT_OUTPUT_DIR,
        cache_dir=DEFAULT_CACHE_DIR,
        env_file=DEFAULT_ENV_FILE,
        legacy_output_dir=legacy_output,
    )


def ensure_cli_workspace() -> GuiWorkspace:
    return ensure_gui_workspace()


def resolve_project_path(path: str | Path | None, default: Path) -> Path:
    if path is None:
        return default
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()
