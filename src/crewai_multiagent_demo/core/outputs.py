from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from crewai_multiagent_demo.utils.files import atomic_write_json, atomic_write_text
from crewai_multiagent_demo.utils.paths import DEFAULT_OUTPUT_DIR


def task_output_text(task_output: object) -> str:
    raw = getattr(task_output, "raw", None)
    return str(raw if raw is not None else task_output)


def create_output_run_dir(output_dir: str | Path = DEFAULT_OUTPUT_DIR, *, run_id: str | None = None) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    identifier = "".join(char for char in (run_id or uuid4().hex) if char.isalnum() or char in "-_")
    for _ in range(128):
        run_dir = root / f"{timestamp}_{identifier or uuid4().hex}"
        try:
            run_dir.mkdir()
            return run_dir
        except FileExistsError:
            identifier = uuid4().hex
    raise RuntimeError("无法分配唯一运行目录")


def write_task_outputs(run_dir: Path, task_outputs: list[dict[str, str]]) -> None:
    tasks_dir = run_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    for index, task_output in enumerate(task_outputs, start=1):
        task_name = task_output.get("task_id") or task_output.get("agent") or f"task_{index}"
        safe_name = "".join(char if char.isalnum() else "_" for char in task_name).strip("_")
        atomic_write_text(tasks_dir / f"{index:02d}_{safe_name or 'task'}.md", task_output.get("output", ""))


def write_run_metadata(
    metadata_file: Path,
    *,
    topic: str,
    model_alias: str,
    model_name: str,
    crewai_model: str,
    elapsed_seconds: float,
    token_usage: dict[str, int],
    status: str = "succeeded",
    error: str | None = None,
) -> None:
    lines = [
        "# 运行元数据",
        "",
        f"- 状态：{status}",
        f"- 主题：{topic}",
        f"- 模型档位：{model_alias}",
        f"- 模型正式名：{model_name}",
        f"- CrewAI 模型字符串：{crewai_model}",
        f"- 总用时：{elapsed_seconds:.2f} 秒",
    ]
    if token_usage:
        lines.extend(
            [
                f"- 总 token：{token_usage.get('total_tokens', 0)}",
                f"- 输入 token：{token_usage.get('prompt_tokens', 0)}",
                f"- 输出 token：{token_usage.get('completion_tokens', 0)}",
                f"- 缓存输入 token：{token_usage.get('cached_prompt_tokens', 0)}",
                f"- 推理 token：{token_usage.get('reasoning_tokens', 0)}",
                f"- 成功请求数：{token_usage.get('successful_requests', 0)}",
            ]
        )
    else:
        lines.append("- token 用量：当前 CrewAI/模型返回中未读取到 token 统计。")
    if error:
        lines.append(f"- 错误：{error.replace(chr(10), ' ')}")
    atomic_write_text(metadata_file, "\n".join(lines) + "\n")


def write_run_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    atomic_write_json(run_dir / "run.json", {"schema_version": 1, **manifest})


def write_run_outputs(
    *,
    output_dir: str | Path,
    full_report: str,
    concise_report: str,
    task_outputs: list[dict[str, str]],
    metadata: dict[str, Any],
    run_dir: Path | None = None,
) -> Path:
    run_dir = run_dir or create_output_run_dir(output_dir)
    atomic_write_text(run_dir / "full_report.md", full_report)
    atomic_write_text(run_dir / "summary_report.md", concise_report)
    write_run_metadata(run_dir / "run_metadata.md", **metadata)
    write_task_outputs(run_dir, task_outputs)
    return run_dir


def write_failed_run_outputs(
    *,
    output_dir: str | Path,
    error: str,
    metadata: dict[str, Any],
    run_dir: Path | None = None,
) -> Path:
    run_dir = run_dir or create_output_run_dir(output_dir)
    failure_report = f"# Run failed\n\n{error}\n"
    atomic_write_text(run_dir / "full_report.md", failure_report)
    atomic_write_text(run_dir / "summary_report.md", failure_report)
    write_run_metadata(run_dir / "run_metadata.md", status="failed", error=error, **metadata)
    return run_dir
