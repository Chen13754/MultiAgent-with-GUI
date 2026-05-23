"""Backward-compatible imports for the original demo scripts."""

from __future__ import annotations

from crewai_multiagent_demo.config.loader import ConfigLoader
from crewai_multiagent_demo.config.schema import config_to_dicts
from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.core.outputs import (
    create_output_run_dir,
    task_output_text,
    write_run_metadata,
    write_task_outputs,
)
from crewai_multiagent_demo.core.runner import (
    DEFAULT_TOPIC,
    extract_token_usage,
    run_workflow,
    usage_to_dict,
)
from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.run_result import RunResult
from crewai_multiagent_demo.domain.tasks import TaskConfig
from crewai_multiagent_demo.llm.model_registry import CREWAI_PROVIDER_PREFIX, MODEL_REGISTRY
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR, PROJECT_ROOT


ROOT = PROJECT_ROOT
CONFIG_DIR = DEFAULT_CONFIG_DIR
AGENTS_FILE = CONFIG_DIR / "agents.json"
TASKS_FILE = CONFIG_DIR / "tasks.json"
OUTPUT_DIR = DEFAULT_OUTPUT_DIR
MODEL_ALIASES = {spec.alias: spec.model_name for spec in MODEL_REGISTRY.list_specs()}


def load_json_file(path):
    return ConfigLoader.load_json_file(path)


def save_json_file(path, data) -> None:
    ConfigLoader.save_json_file(path, data)


def load_agent_configs() -> list[AgentConfig]:
    return ConfigLoader(CONFIG_DIR).load_agents()


def load_task_configs() -> list[TaskConfig]:
    return ConfigLoader(CONFIG_DIR).load_tasks()


def default_model_alias() -> str:
    return MODEL_REGISTRY.default_alias()


def formal_model_name(model_alias: str) -> str:
    return MODEL_REGISTRY.resolve(model_alias).model_name


def crewai_model_name(model_name: str) -> str:
    if model_name.startswith(CREWAI_PROVIDER_PREFIX):
        return model_name
    return f"{CREWAI_PROVIDER_PREFIX}{model_name}"


def run_crew(**kwargs) -> RunResult:
    return run_workflow(**kwargs)
