from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    model_name: str
    description: str
    provider: str = "deepseek"
    api_key_env_names: tuple[str, ...] = ("DEEPSEEK_API_KEY",)

    @property
    def crewai_model(self) -> str:
        if "/" in self.model_name:
            return self.model_name
        return f"{self.provider}/{self.model_name}"


class ModelRegistry:
    def __init__(
        self,
        models: dict[str, ModelSpec] | None = None,
        *,
        default_alias: str | None = None,
    ) -> None:
        self._models = models or {
            "flash": ModelSpec("flash", "deepseek-v4-flash", "更快，适合日常迭代"),
            "pro": ModelSpec("pro", "deepseek-v4-pro", "能力更强，适合复杂问题"),
        }
        if not self._models:
            raise ValueError("模型注册表不能为空")
        for alias, spec in self._models.items():
            if alias != spec.alias:
                raise ValueError(f"模型键与 alias 不一致: {alias} != {spec.alias}")
        self._default_alias = default_alias or next(iter(self._models))
        if self._default_alias not in self._models:
            raise ValueError(f"默认模型档位不存在: {self._default_alias}")

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
        return self._default_alias

    def list_specs(self) -> list[ModelSpec]:
        return [self._models[alias] for alias in self.aliases]


MODEL_REGISTRY = ModelRegistry(default_alias="flash")
CREWAI_PROVIDER_PREFIX = "deepseek/"
