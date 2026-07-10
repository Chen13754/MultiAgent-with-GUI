from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from threading import Thread

from crewai_multiagent_demo.utils.paths import GuiWorkspace
from scripts.fake_openai_server import Handler
from web_gui_app import run_provider_e2e


def workspace(config_dir, output_dir) -> GuiWorkspace:
    return GuiWorkspace(
        config_dir=config_dir,
        output_dir=output_dir,
        cache_dir=output_dir.parent / ".cache",
        env_file=output_dir.parent / ".env",
        legacy_output_dir=None,
    )


def test_local_openai_compatible_provider_e2e(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "workflow.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "agents": [
                    {
                        "id": "tester",
                        "role": "Test agent",
                        "goal": "Return the local response",
                        "backstory": "Used only for an offline provider test",
                        "enabled": True,
                    }
                ],
                "tasks": [
                    {
                        "id": "report",
                        "name": "Report",
                        "description": "Respond to {topic}",
                        "expected_output": "A short response",
                        "agent_id": "tester",
                        "context_task_ids": [],
                        "artifact_role": "full_report",
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "local-e2e-key")
        monkeypatch.setenv("DEEPSEEK_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
        result = run_provider_e2e(workspace(config_dir, tmp_path / "outputs"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result == 0
    manifests = list((tmp_path / "outputs").glob("*/run.json"))
    assert len(manifests) == 1
    assert json.loads(manifests[0].read_text(encoding="utf-8"))["status"] == "succeeded"


def test_provider_e2e_rejects_external_base_url(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    assert run_provider_e2e(workspace(tmp_path, tmp_path)) == 2
