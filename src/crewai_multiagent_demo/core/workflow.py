from __future__ import annotations

from crewai_multiagent_demo.config.loader import AppConfig, ConfigLoader
from crewai_multiagent_demo.config.validation import validate_configs


def load_and_validate_workflow(config_dir: str | None = None) -> AppConfig:
    loader = ConfigLoader(config_dir) if config_dir else ConfigLoader()
    return loader.load(validate=True)


def validate_workflow(config: AppConfig) -> None:
    validate_configs(config.agents, config.tasks)
