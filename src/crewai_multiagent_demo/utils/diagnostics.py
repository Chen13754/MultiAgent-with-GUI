from __future__ import annotations

import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def create_diagnostics_archive(cache_dir: Path, output_dir: Path) -> Path:
    diagnostics_dir = cache_dir / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    archive = diagnostics_dir / f"diagnostics-{datetime.now():%Y%m%d-%H%M%S}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        system = {
            "python": sys.version,
            "platform": platform.platform(),
            "executable": Path(sys.executable).name,
            "frozen": bool(getattr(sys, "frozen", False)),
        }
        bundle.writestr("system.json", json.dumps(system, ensure_ascii=False, indent=2))
        log_dir = cache_dir / "logs"
        if log_dir.exists():
            for log_file in log_dir.glob("*.log*"):
                if log_file.is_file():
                    bundle.write(log_file, f"logs/{log_file.name}")
        if output_dir.exists():
            run_dirs = sorted((path for path in output_dir.iterdir() if path.is_dir()), reverse=True)[:10]
            for run_dir in run_dirs:
                for name in ("run.json", "events.json", "run_metadata.md"):
                    source = run_dir / name
                    if source.exists():
                        bundle.write(source, f"runs/{run_dir.name}/{name}")
    return archive
