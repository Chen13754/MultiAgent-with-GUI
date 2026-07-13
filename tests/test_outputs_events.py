from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from crewai_multiagent_demo.core.events import EventEmitter, write_event_log
from crewai_multiagent_demo.core.outputs import create_output_run_dir, write_run_metadata, write_task_outputs


def test_output_directory_creation_is_unique(tmp_path) -> None:
    first = create_output_run_dir(tmp_path)
    second = create_output_run_dir(tmp_path)

    assert first.exists()
    assert second.exists()
    assert first != second


def test_output_directory_creation_is_safe_under_concurrency(tmp_path) -> None:
    with ThreadPoolExecutor(max_workers=32) as pool:
        paths = list(pool.map(lambda _: create_output_run_dir(tmp_path), range(64)))

    assert len(paths) == 64
    assert len(set(paths)) == 64
    assert all(path.exists() for path in paths)


def test_event_writing(tmp_path) -> None:
    emitter = EventEmitter()
    emitter.emit("run_started", model="flash")

    write_event_log(tmp_path, emitter.events)

    data = json.loads((tmp_path / "events.json").read_text(encoding="utf-8"))
    assert data[0]["type"] == "run_started"
    assert data[0]["model"] == "flash"


def test_task_outputs_and_metadata_writing(tmp_path) -> None:
    write_task_outputs(tmp_path, [{"agent": "Problem Analyst", "output": "hello"}])
    write_run_metadata(
        tmp_path / "run_metadata.md",
        topic="topic",
        model_alias="flash",
        model_name="deepseek-v4-flash",
        crewai_model="deepseek/deepseek-v4-flash",
        elapsed_seconds=1.2,
        token_usage={"total_tokens": 10},
    )

    assert (tmp_path / "tasks" / "01_Problem_Analyst.md").read_text(encoding="utf-8") == "hello"
    metadata = (tmp_path / "run_metadata.md").read_text(encoding="utf-8")
    assert "模型档位：flash" in metadata
    assert "总 token：10" in metadata
