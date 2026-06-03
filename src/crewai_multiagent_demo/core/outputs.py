from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from crewai_multiagent_demo.utils.paths import DEFAULT_OUTPUT_DIR


def task_output_text(task_output: object) -> str:
    raw = getattr(task_output, "raw", None)
    return str(raw if raw is not None else task_output)


def create_output_run_dir(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    root = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / timestamp
    suffix = 1

    while run_dir.exists():
        run_dir = root / f"{timestamp}_{suffix:02d}"
        suffix += 1

    run_dir.mkdir(parents=True)
    return run_dir


def write_task_outputs(run_dir: Path, task_outputs: list[dict[str, str]]) -> None:
    tasks_dir = run_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    for index, task_output in enumerate(task_outputs, start=1):
        agent = task_output.get("agent") or f"task_{index}"
        safe_agent = "".join(char if char.isalnum() else "_" for char in agent).strip("_")
        filename = f"{index:02d}_{safe_agent or 'task'}.md"
        (tasks_dir / filename).write_text(task_output.get("output", ""), encoding="utf-8")


def write_run_metadata(
    metadata_file: Path,
    *,
    topic: str,
    model_alias: str,
    model_name: str,
    crewai_model: str,
    elapsed_seconds: float,
    token_usage: dict[str, int],
) -> None:
    lines = [
        "# 运行元数据",
        "",
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

    metadata_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_outputs(
    *,
    output_dir: str | Path,
    full_report: str,
    concise_report: str,
    task_outputs: list[dict[str, str]],
    metadata: dict[str, Any],
) -> Path:
    run_dir = create_output_run_dir(output_dir)
    (run_dir / "full_report.md").write_text(full_report, encoding="utf-8")
    (run_dir / "summary_report.md").write_text(concise_report, encoding="utf-8")
    write_run_metadata(run_dir / "run_metadata.md", **metadata)
    write_task_outputs(run_dir, task_outputs)
    return run_dir


def write_failed_run_outputs(
    *,
    output_dir: str | Path,
    error: str,
    metadata: dict[str, Any],
) -> Path:
    run_dir = create_output_run_dir(output_dir)
    failure_report = f"# Run failed\n\n{error}\n"
    (run_dir / "full_report.md").write_text(failure_report, encoding="utf-8")
    (run_dir / "summary_report.md").write_text(failure_report, encoding="utf-8")
    write_run_metadata(run_dir / "run_metadata.md", **metadata)
    with (run_dir / "run_metadata.md").open("a", encoding="utf-8") as file:
        file.write(f"- status: failed\n- error: {error}\n")
    return run_dir
