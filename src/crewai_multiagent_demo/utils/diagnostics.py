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
        if output_dir.exists():
            run_dirs = sorted((path for path in output_dir.iterdir() if path.is_dir()), reverse=True)[:10]
            for run_dir in run_dirs:
                manifest_file = run_dir / "run.json"
                if not manifest_file.exists():
                    continue
                try:
                    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                except (OSError, ValueError, TypeError):
                    continue
                safe_manifest = {
                    key: manifest.get(key)
                    for key in (
                        "schema_version",
                        "run_id",
                        "status",
                        "model_alias",
                        "model_name",
                        "crewai_model",
                        "elapsed_seconds",
                        "config_revision",
                    )
                    if key in manifest
                }
                bundle.writestr(
                    f"runs/{run_dir.name}/manifest.json",
                    json.dumps(safe_manifest, ensure_ascii=False, indent=2),
                )
    return archive
