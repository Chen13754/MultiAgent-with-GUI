from __future__ import annotations

from crewai_multiagent_demo.domain.run_request import RunRequest
from crewai_multiagent_demo.gui.run_process import write_process_trace


def test_worker_trace_is_persisted_without_replacing_user_error(tmp_path) -> None:
    request = RunRequest.create(
        topic="topic",
        model_alias="flash",
        config_dir=tmp_path / "config",
        output_dir=tmp_path / "outputs",
    )
    run_dir = request.output_dir / f"20260713_120000_{request.run_id}"
    run_dir.mkdir(parents=True)

    write_process_trace(request, "Traceback (most recent call last):\n  worker failure")

    assert "worker failure" in (run_dir / "process_error.txt").read_text(encoding="utf-8")
