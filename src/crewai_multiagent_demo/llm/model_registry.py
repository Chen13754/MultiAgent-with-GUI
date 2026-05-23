from __future__ import annotations

import os
from dataclasses import dataclass


CREWAI_PROVIDER_PREFIX = "deepseek/"


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    model_name: str
    description: str

    @property
    def crewai_model(self) -> str:
        if self.model_name.startswith(CREWAI_PROVIDER_PREFIX):
            return self.model_name
        return f"{CREWAI_PROVIDER_PREFIX}{self.model_name}"


class ModelRegistry:
    def __init__(self, models: dict[str, ModelSpec] | None = None) -> None:
        self._models = models or {
            "flash": ModelSpec("flash", "deepseek-v4-flash", "更快，适合日常迭代"),
            "pro": ModelSpec("pro", "deepseek-v4-pro", "能力更强，适合复杂问题"),
        }

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(sorted(self._models))

    def resolve(self, alias: str | None) -> ModelSpec:
        resolved_alias = (alias or self.default_alias()).strip()
        if resolved_alias not in self._models:
            raise ValueError(f"未知模型档位: {resolved_alias}。可用档位: {', '.join(self.aliases)}")
        return self._models[resolved_alias]

    def default_alias(self) -> str:
        configured_alias = os.getenv("MODEL_VARIANT", "")
        if configured_alias in self._models:
            return configured_alias

        configured_model = (
            os.getenv("MODEL")
            or os.getenv("MODEL_NAME")
            or os.getenv("OPENAI_MODEL_NAME")
            or ""
        )
        for alias, spec in self._models.items():
            if configured_model in {spec.model_name, spec.crewai_model}:
                return alias
        return "flash"

    def list_specs(self) -> list[ModelSpec]:
        return [self._models[alias] for alias in self.aliases]


MODEL_REGISTRY = ModelRegistry()
