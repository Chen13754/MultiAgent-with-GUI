from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
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
WINDOWS_VERSION_FILE = PROJECT_ROOT / "scripts" / "windows_version_info.txt"


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


def write_checksum(path: Path) -> Path:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksum = path.with_suffix(path.suffix + ".sha256")
    checksum.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return checksum


def project_version() -> str:
    for line in (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version ="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("Project version is missing from pyproject.toml")


def sign_and_notarize_bundle(bundle: Path) -> None:
    required = os.getenv("REQUIRE_SIGNING") == "1"
    if platform.system() == "Windows":
        certificate = os.getenv("WINDOWS_SIGN_PFX_PATH")
        password = os.getenv("WINDOWS_SIGN_PFX_PASSWORD")
        if not certificate or not password:
            if required:
                raise RuntimeError("Windows signing credentials are required for this release build")
            print("Development build: Windows code signing skipped")
            return
        signtool = os.getenv("SIGNTOOL_PATH") or shutil.which("signtool")
        if not signtool:
            raise RuntimeError("signtool was not found")
        run(
            [
                signtool,
                "sign",
                "/fd",
                "SHA256",
                "/td",
                "SHA256",
                "/tr",
                "http://timestamp.digicert.com",
                "/f",
                certificate,
                "/p",
                password,
                str(bundle / "MultiagentStudio.exe"),
            ]
        )
        return

    if platform.system() == "Darwin":
        identity = os.getenv("MACOS_SIGN_IDENTITY")
        notary_profile = os.getenv("MACOS_NOTARY_PROFILE")
        notary_keychain = os.getenv("MACOS_NOTARY_KEYCHAIN")
        if not identity or not notary_profile:
            if required:
                raise RuntimeError("macOS signing and notarization credentials are required for this release build")
            print("Development build: macOS signing and notarization skipped")
            return
        run(["codesign", "--deep", "--force", "--options", "runtime", "--sign", identity, str(bundle)])
        notary_archive = PROJECT_ROOT / "dist" / "MultiagentStudio-notary.zip"
        run(["ditto", "-c", "-k", "--keepParent", str(bundle), str(notary_archive)])
        try:
            notary_command = [
                "xcrun",
                "notarytool",
                "submit",
                str(notary_archive),
                "--keychain-profile",
                notary_profile,
            ]
            if notary_keychain:
                notary_command.extend(["--keychain", notary_keychain])
            run([*notary_command, "--wait"])
            run(["xcrun", "stapler", "staple", str(bundle)])
        finally:
            notary_archive.unlink(missing_ok=True)


def check_prerequisites(*, require_frontend_dist: bool = False) -> None:
    required_paths = [
        PROJECT_ROOT / "src" / "web_gui_app.py",
        PROJECT_ROOT / "config" / "workflow.json",
        PROJECT_ROOT / "contracts" / "studio.schema.json",
    ]
    if require_frontend_dist:
        required_paths.append(FRONTEND_DIST / "index.html")
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
    check_prerequisites(require_frontend_dist=False)
    if args.check:
        return 0

    store_dir = Path(os.getenv("PNPM_STORE_DIR", PROJECT_ROOT / ".cache" / "pnpm-store"))
    store_dir.mkdir(parents=True, exist_ok=True)
    pnpm = pnpm_command()
    run([*pnpm, "install", "--frozen-lockfile", "--store-dir", str(store_dir)], cwd=FRONTEND_DIR)
    run([*pnpm, "run", "build"], cwd=FRONTEND_DIR)
    check_prerequisites(require_frontend_dist=True)

    separator = ";" if os.name == "nt" else ":"
    config_data = f"{PROJECT_ROOT / 'config'}{separator}config"
    ui_data = f"{FRONTEND_DIST}{separator}webui"
    pyinstaller_command = [
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
            "--collect-data",
            "crewai_multiagent_demo",
            "--exclude-module",
            "chromadb",
            "src/web_gui_app.py",
        ]
    if os.name == "nt":
        pyinstaller_command[-1:-1] = ["--version-file", str(WINDOWS_VERSION_FILE)]
    run(pyinstaller_command)
    bundle = PROJECT_ROOT / "dist" / ("MultiagentStudio.app" if platform.system() == "Darwin" else "MultiagentStudio")
    if not bundle.exists():
        raise RuntimeError(f"PyInstaller bundle was not produced: {bundle}")
    commit = os.getenv("GITHUB_SHA", "local")
    (bundle / "build-info.json").write_text(
        json.dumps(
            {"version": project_version(), "target": target_name(), "commit": commit},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    sign_and_notarize_bundle(bundle)
    archive = make_archive(bundle)
    checksum = write_checksum(archive)
    print(f"Portable bundle ready: {archive}")
    print(f"SHA-256 ready: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
