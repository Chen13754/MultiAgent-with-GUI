from crewai_multiagent_demo.gui.state import (
    RunStatus,
    normalize_status,
    normalize_task_rows,
    progress_from_events,
    status_label,
    task_rows_for_editor,
)


def test_status_label_tolerates_unknown_values() -> None:
    assert normalize_status("running") == RunStatus.RUNNING
    assert normalize_status("unknown") == RunStatus.IDLE
    assert status_label("running") == "运行中"
    assert status_label("unknown") == "待运行"


def test_progress_from_events_counts_completed_tasks() -> None:
    events = [
        {"type": "run_started"},
        {"type": "task_completed"},
        {"type": "task_completed"},
    ]
    assert progress_from_events(events) == 50


def test_task_rows_round_trip_context_task_ids() -> None:
    rows = [
        {
            "id": "review",
            "context_task_ids": ["analysis", "solution"],
            "enabled": True,
        }
    ]

    editable = task_rows_for_editor(rows)
    assert editable[0]["context_task_ids"] == "analysis, solution"

    normalized = normalize_task_rows(editable)
    assert normalized[0]["context_task_ids"] == ["analysis", "solution"]

