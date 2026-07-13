from __future__ import annotations

import json
from zipfile import ZipFile

from crewai_multiagent_demo.utils.diagnostics import create_diagnostics_archive


def test_diagnostics_archive_omits_user_content_and_raw_events(tmp_path) -> None:
    output_dir = tmp_path / "outputs"
    run_dir = output_dir / "20260713_120000_run"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "run-1",
                "status": "succeeded",
                "topic": "PRIVATE TOPIC",
                "model_alias": "flash",
                "config_revision": "revision-1",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "events.json").write_text(json.dumps([{"output": "PRIVATE OUTPUT"}]), encoding="utf-8")
    (run_dir / "run_metadata.md").write_text("PRIVATE TOPIC", encoding="utf-8")

    archive = create_diagnostics_archive(tmp_path / "cache", output_dir)

    with ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        content = "\n".join(bundle.read(name).decode("utf-8") for name in names)

    assert "system.json" in names
    assert "runs/20260713_120000_run/manifest.json" in names
    assert not any(name.endswith("events.json") or name.endswith("run_metadata.md") for name in names)
    assert "PRIVATE TOPIC" not in content
    assert "PRIVATE OUTPUT" not in content
