from __future__ import annotations

import argparse
import json
import re
from importlib.metadata import distributions
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def component(name: str, version: str, kind: str) -> dict[str, str]:
    return {"type": kind, "name": name, "version": version}


def project_version() -> str:
    for line in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*version\s*=\s*[\"']([^\"']+)[\"']", line)
        if match:
            return match.group(1)
    raise RuntimeError("Project version is missing from pyproject.toml")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a minimal CycloneDX software bill of materials.")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "sbom.cdx.json")
    args = parser.parse_args()
    python_components = sorted(
        {
            (str(dist.metadata["Name"] if "Name" in dist.metadata else "unknown"), dist.version)
            for dist in distributions()
        }
    )
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    js_components = [
        component(name, constraint, "library")
        for group in ("dependencies", "devDependencies")
        for name, constraint in package.get(group, {}).items()
    ]
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid4()}",
        "version": 1,
        "metadata": {"component": component("MultiagentStudio", project_version(), "application")},
        "components": [component(name, version, "library") for name, version in python_components] + js_components,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
