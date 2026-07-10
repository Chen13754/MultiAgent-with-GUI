from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
PYTHON = Path(sys.executable)


def run(command: list[str], *, cwd: Path = PROJECT_ROOT) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def pnpm_command() -> list[str]:
    node = os.getenv("PNPM_NODE")
    script = os.getenv("PNPM_SCRIPT")
    if node and script:
        return [node, script]
    configured = os.getenv("PNPM")
    if configured:
        return [configured]
    found = shutil.which("pnpm")
    if found:
        return [found]
    corepack = shutil.which("corepack")
    if corepack:
        return [corepack, "pnpm"]
    raise RuntimeError("pnpm was not found. Install it with Corepack or set the PNPM environment variable.")


def target_name() -> str:
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    system = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system())
    if system is None:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")
    return f"{system}-{arch}"


def make_archive(bundle: Path) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    archive_base = dist_dir / f"MultiagentStudio-{target_name()}"
    if platform.system() == "Linux":
        result = shutil.make_archive(str(archive_base), "gztar", root_dir=bundle.parent, base_dir=bundle.name)
    else:
        result = shutil.make_archive(str(archive_base), "zip", root_dir=bundle.parent, base_dir=bundle.name)
    return Path(result)


def check_prerequisites() -> None:
    required_paths = [
        PROJECT_ROOT / "src" / "web_gui_app.py",
        PROJECT_ROOT / "config" / "agents.json",
        PROJECT_ROOT / "config" / "tasks.json",
        FRONTEND_DIST / "index.html",
    ]
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    if missing_paths:
        raise RuntimeError("Missing build inputs: " + ", ".join(missing_paths))

    modules = (
        "PyInstaller",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
    )
    missing_modules = [module for module in modules if importlib.util.find_spec(module) is None]
    if missing_modules:
        raise RuntimeError("Missing Python build modules: " + ", ".join(missing_modules))

    manager = pnpm_command()
    print(f"Build prerequisites ready: target={target_name()}, package_manager={' '.join(manager)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Multiagent Studio desktop bundle.")
    parser.add_argument("--check", action="store_true", help="Validate build inputs without packaging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    check_prerequisites()
    if args.check:
        return 0

    store_dir = Path(os.getenv("PNPM_STORE_DIR", PROJECT_ROOT / ".cache" / "pnpm-store"))
    store_dir.mkdir(parents=True, exist_ok=True)
    pnpm = pnpm_command()
    run([*pnpm, "install", "--frozen-lockfile", "--store-dir", str(store_dir)], cwd=FRONTEND_DIR)
    run([*pnpm, "run", "build"], cwd=FRONTEND_DIR)
    if not (FRONTEND_DIST / "index.html").exists():
        raise RuntimeError("Frontend build did not produce dist/index.html")

    separator = ";" if os.name == "nt" else ":"
    config_data = f"{PROJECT_ROOT / 'config'}{separator}config"
    ui_data = f"{FRONTEND_DIST}{separator}webui"
    run(
        [
            str(PYTHON),
            "-s",
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--windowed",
            "--name",
            "MultiagentStudio",
            "--paths",
            "src",
            "--add-data",
            config_data,
            "--add-data",
            ui_data,
            "--collect-all",
            "PySide6.QtWebEngineCore",
            "--collect-all",
            "PySide6.QtWebEngineWidgets",
            "--collect-all",
            "PySide6.QtWebChannel",
            "src/web_gui_app.py",
        ]
    )
    bundle = PROJECT_ROOT / "dist" / ("MultiagentStudio.app" if platform.system() == "Darwin" else "MultiagentStudio")
    if not bundle.exists():
        raise RuntimeError(f"PyInstaller bundle was not produced: {bundle}")
    archive = make_archive(bundle)
    print(f"Portable bundle ready: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
