from __future__ import annotations

from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


RUN_LOCK_REASON = "工作流正在运行，完成后可切换页面或修改配置。"


def normalize_status(value: object) -> RunStatus:
    try:
        return RunStatus(str(value))
    except ValueError:
        return RunStatus.IDLE


def status_label(status: object) -> str:
    labels = {
        RunStatus.IDLE: "待运行",
        RunStatus.RUNNING: "运行中",
        RunStatus.SUCCEEDED: "已完成",
        RunStatus.FAILED: "失败",
        RunStatus.CANCELLED: "已取消",
    }
    return labels[normalize_status(status)]


def event_label(event_type: str) -> str:
    labels = {
        "run_started": "运行开始",
        "task_started": "任务开始",
        "task_completed": "任务完成",
        "task_failed": "任务失败",
        "task_cancelled": "任务取消",
        "run_completed": "运行完成",
        "run_failed": "运行失败",
        "run_cancelled": "运行取消",
        "run_timeout": "运行超时",
    }
    return labels.get(event_type, event_type)


def progress_from_events(events: list[dict[str, Any]], total_tasks: int = 4) -> int:
    completed = sum(1 for item in events if item.get("type") == "task_completed")
    if total_tasks <= 0:
        return 10
    return min(95, 10 + int(completed / total_tasks * 85))


def task_rows_for_editor(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    editable = []
    for row in rows:
        copied = dict(row)
        copied["context_task_ids"] = ", ".join(copied.get("context_task_ids", []))
        editable.append(copied)
    return editable


def normalize_task_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        copied = dict(row)
        context_value = copied.get("context_task_ids", "")
        if isinstance(context_value, list):
            context_ids = [str(item).strip() for item in context_value if str(item).strip()]
        else:
            context_ids = [item.strip() for item in str(context_value).split(",") if item.strip()]
        copied["context_task_ids"] = context_ids
        normalized.append(copied)
    return normalized
