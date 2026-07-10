from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS_FILE = PROJECT_ROOT / "security" / "pip-audit-exceptions.json"


def active_exception_ids(*, today: date | None = None) -> list[str]:
    payload = json.loads(EXCEPTIONS_FILE.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError("Unsupported dependency-audit exception schema")
    current = today or date.today()
    result: list[str] = []
    for item in payload.get("exceptions", []):
        vulnerability_id = str(item.get("id", "")).strip()
        rationale = str(item.get("rationale", "")).strip()
        expires = date.fromisoformat(str(item.get("expires", "")))
        if not vulnerability_id or not rationale:
            raise RuntimeError("Every dependency-audit exception needs an id and rationale")
        if expires < current:
            raise RuntimeError(f"Dependency-audit exception expired: {vulnerability_id} ({expires})")
        result.append(vulnerability_id)
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pip-audit with checked, expiring exceptions.")
    parser.add_argument("--dry-run", action="store_true", help="Only validate and print active exceptions.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    exceptions = active_exception_ids()
    print("Active dependency-audit exceptions:", ", ".join(exceptions) or "none")
    if args.dry_run:
        return 0

    cache_dir = PROJECT_ROOT / ".cache" / "pip-audit"
    cache_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--requirement",
        str(PROJECT_ROOT / "requirements.lock"),
        "--progress-spinner",
        "off",
        "--cache-dir",
        str(cache_dir),
    ]
    for vulnerability_id in exceptions:
        command.extend(["--ignore-vuln", vulnerability_id])
    return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
