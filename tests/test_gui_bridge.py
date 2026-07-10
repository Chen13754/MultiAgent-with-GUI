from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from crewai_multiagent_demo.domain.run_result import RunResult
from crewai_multiagent_demo.gui.bridge import StudioBridge


def write_config(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "agents.json").write_text(
        json.dumps(
            [
                {
                    "id": "analyst",
                    "role": "Analyst",
                    "goal": "Analyze",
                    "backstory": "Careful",
                    "enabled": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "tasks.json").write_text(
        json.dumps(
            [
                {
                    "id": "analysis",
                    "name": "Analysis",
                    "description": "Analyze {topic}",
                    "expected_output": "Report",
                    "agent_id": "analyst",
                    "context_task_ids": [],
                    "enabled": True,
                }
            ]
        ),
        encoding="utf-8",
    )


def response(raw: str) -> dict[str, object]:
    return json.loads(raw)


def test_bridge_bootstrap_and_save_keep_task_schema(tmp_path) -> None:
    config_dir = tmp_path / "config"
    write_config(config_dir)
    bridge = StudioBridge(config_dir=config_dir, output_dir=tmp_path / "outputs", api_key_checker=lambda _model: True)

    initial = response(bridge.bootstrap())
    assert initial["ok"] is True
    config = initial["data"]["config"]
    task = config["tasks"][0]
    assert task["name"] == "Analysis"
    assert task["agent_id"] == "analyst"
    assert task["context_task_ids"] == []

    config["tasks"][0]["name"] = "Updated analysis"
    saved = response(bridge.saveConfig("tasks", json.dumps(config["tasks"])))
    assert saved["ok"] is True
    persisted = json.loads((config_dir / "workflow.json").read_text(encoding="utf-8"))
    assert persisted["tasks"][0]["name"] == "Updated analysis"
    assert persisted["tasks"][0]["agent_id"] == "analyst"


def test_bridge_reports_missing_api_key_without_starting_worker(tmp_path) -> None:
    config_dir = tmp_path / "config"
    write_config(config_dir)
    bridge = StudioBridge(config_dir=config_dir, output_dir=tmp_path / "outputs", api_key_checker=lambda _model: False)

    started = response(bridge.startRun("topic", "flash"))

    assert started == {"ok": False, "code": "missing_api_key", "message": started["message"]}
    state = response(bridge.bootstrap())["data"]["runState"]
    assert state["status"] == "failed"
    assert bridge.is_running() is False


def test_bridge_reads_history_from_event_log_and_legacy_metadata(tmp_path) -> None:
    config_dir = tmp_path / "config"
    output_dir = tmp_path / "outputs"
    write_config(config_dir)
    run = output_dir / "20260710_100000"
    run.mkdir(parents=True)
    (run / "events.json").write_text(
        json.dumps(
            [
                {"type": "run_started", "model": "pro"},
                {"type": "run_completed", "elapsed_seconds": 4.25},
            ]
        ),
        encoding="utf-8",
    )
    (run / "summary_report.md").write_text("summary", encoding="utf-8")
    (run / "full_report.md").write_text("full", encoding="utf-8")
    (run / "run_metadata.md").write_text("- 模型档位：pro\n- 总用时：4.25 秒\n", encoding="utf-8")
    bridge = StudioBridge(config_dir=config_dir, output_dir=output_dir, api_key_checker=lambda _model: True)

    history = response(bridge.bootstrap())["data"]["history"]
    assert history[0]["modelAlias"] == "pro"
    assert history[0]["elapsedSeconds"] == 4.25
    detail = response(bridge.loadHistory(history[0]["id"]))
    assert detail["data"]["summary"] == "summary"
    assert response(bridge.loadHistory("current:../outside"))["code"] == "history_missing"


def test_bridge_streams_fake_workflow_result(tmp_path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    config_dir = tmp_path / "config"
    output_dir = tmp_path / "outputs"
    write_config(config_dir)

    received = {}

    def fake_runner(**kwargs):
        received.update(kwargs)
        kwargs["on_event"]({"type": "run_started", "agent": "analyst"})
        kwargs["on_event"]({"type": "task_completed", "agent": "analyst"})
        run_dir = output_dir / "20260710_110000"
        run_dir.mkdir(parents=True)
        return RunResult(
            topic=kwargs["topic"],
            model_alias=kwargs["model_alias"],
            model_name="Mock",
            crewai_model="mock/model",
            elapsed_seconds=0.2,
            token_usage={},
            run_dir=run_dir,
            full_report="full",
            concise_report="summary",
            task_outputs=[{"agent": "analyst", "output": "done"}],
            events=[],
        )

    bridge = StudioBridge(
        config_dir=config_dir,
        output_dir=output_dir,
        runner=fake_runner,
        api_key_checker=lambda _model: True,
    )
    started = response(bridge.startRun("topic", "flash"))
    assert started["ok"] is True
    deadline = time.monotonic() + 2
    while bridge.is_running() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    state = response(bridge.bootstrap())["data"]["runState"]
    assert state["status"] == "succeeded"
    assert state["progress"] == 100
    assert state["result"]["summary"] == "summary"
    assert received["config_dir"] == config_dir
    assert received["output_dir"] == output_dir
    assert received["run_id"] == state["runId"]


def test_bridge_can_recover_from_corrupt_workflow(tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "workflow.json").write_text("{", encoding="utf-8")
    bridge = StudioBridge(config_dir=config_dir, output_dir=tmp_path / "outputs", api_key_checker=lambda _: True)

    failed = response(bridge.bootstrap())
    recovered = response(bridge.resetConfig())

    assert failed["ok"] is False
    assert failed["code"] == "bootstrap_failed"
    assert recovered["ok"] is True
    assert recovered["data"]["protocolVersion"] == 1
