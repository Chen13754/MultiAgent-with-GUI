from __future__ import annotations

import argparse
import sys
from pathlib import Path

from crewai_multiagent_demo.config.loader import ConfigLoader
from crewai_multiagent_demo.core.runner import DEFAULT_TOPIC, run_workflow
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY
from crewai_multiagent_demo.utils.environment import load_project_env
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR, ensure_cli_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行和管理 CrewAI 多 Agent 通用问题解决工作流。"
    )
    parser.add_argument(
        "--config-dir",
        default=str(DEFAULT_CONFIG_DIR),
        help="配置目录，默认 config/",
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="运行 workflow")
    run_parser.add_argument("topic", nargs="*", help="要分析和解决的问题主题")
    run_parser.add_argument("--model", choices=MODEL_REGISTRY.aliases, default=None)
    run_parser.add_argument("--config-dir", default=str(DEFAULT_CONFIG_DIR))
    run_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    validate_parser = subparsers.add_parser("validate", help="只校验配置，不调用模型")
    validate_parser.add_argument("--config-dir", default=str(DEFAULT_CONFIG_DIR))
    validate_parser.set_defaults(command="validate")

    list_models_parser = subparsers.add_parser("list-models", help="列出可用模型档位")
    list_models_parser.set_defaults(command="list-models")

    list_config_parser = subparsers.add_parser("list-config", help="列出当前启用的 agents/tasks")
    list_config_parser.add_argument("--config-dir", default=str(DEFAULT_CONFIG_DIR))
    list_config_parser.set_defaults(command="list-config")

    return parser


def _normalize_legacy_args(argv: list[str] | None) -> list[str] | None:
    if argv is None:
        return None
    commands = {"run", "validate", "list-models", "list-config", "-h", "--help"}
    if not argv:
        return ["run"]
    if argv[0] not in commands:
        return ["run", *argv]
    return argv


def main(argv: list[str] | None = None) -> None:
    workspace = ensure_cli_workspace()
    load_project_env(workspace.env_file)
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(_normalize_legacy_args(argv))
    command = args.command or "run"

    try:
        if command == "run":
            topic = " ".join(args.topic).strip() or DEFAULT_TOPIC
            result = run_workflow(
                topic=topic,
                model_alias=args.model,
                config_dir=Path(args.config_dir),
                output_dir=Path(args.output_dir),
            )
            print("\n===== FULL REPORT =====\n")
            print(result.full_report)
            print(f"\n已保存到: {result.run_dir / 'full_report.md'}")
            print("\n===== CONCISE REPORT =====\n")
            print(result.concise_report)
            print(f"\n精简报告已保存到: {result.run_dir / 'summary_report.md'}")
            print("\n===== RUN STATS =====\n")
            print(f"模型: {result.model_alias} ({result.model_name})")
            print(f"CrewAI 模型字符串: {result.crewai_model}")
            print(f"总用时: {result.elapsed_seconds:.2f} 秒")
            if result.token_usage:
                print(f"总 token: {result.token_usage.get('total_tokens', 0)}")
                print(f"输入 token: {result.token_usage.get('prompt_tokens', 0)}")
                print(f"输出 token: {result.token_usage.get('completion_tokens', 0)}")
            else:
                print("token 用量: 当前 CrewAI/模型返回中未读取到 token 统计。")
            print(f"运行元数据已保存到: {result.run_dir / 'run_metadata.md'}")
            return

        if command == "validate":
            config = ConfigLoader(args.config_dir).load(validate=True)
            print(f"配置校验通过: {len(config.agents)} agents, {len(config.tasks)} tasks")
            return

        if command == "list-models":
            for spec in MODEL_REGISTRY.list_specs():
                default_marker = " (default)" if spec.alias == MODEL_REGISTRY.default_alias() else ""
                print(f"{spec.alias}{default_marker}: {spec.model_name} -> {spec.crewai_model}")
            return

        if command == "list-config":
            config = ConfigLoader(args.config_dir).load(validate=True)
            print("Enabled agents:")
            for agent in config.agents:
                if agent.enabled:
                    print(f"- {agent.id}: {agent.role}")
            print("\nEnabled tasks:")
            for task in config.tasks:
                if task.enabled:
                    deps = ", ".join(task.context_task_ids) or "-"
                    print(f"- {task.id}: {task.name} (agent={task.agent_id}, deps={deps})")
            return

    except Exception as exc:
        raise SystemExit(f"错误: {exc}") from exc
