from __future__ import annotations

from dataclasses import dataclass

from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY, ModelRegistry, ModelSpec


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    base_url_env: str
    api_key_env_names: tuple[str, ...]
    request_timeout_seconds: float = 180.0
    max_retries: int = 2


PROVIDERS = {
    "deepseek": ProviderSpec(
        name="deepseek",
        base_url_env="DEEPSEEK_BASE_URL",
        api_key_env_names=("DEEPSEEK_API_KEY",),
    )
}


def resolve_model(alias: str | None, registry: ModelRegistry = MODEL_REGISTRY) -> ModelSpec:
    return registry.resolve(alias)


def provider_for_model(model: ModelSpec) -> ProviderSpec:
    try:
        return PROVIDERS[model.provider]
    except KeyError as exc:
        raise ValueError(f"未配置 LLM provider: {model.provider}") from exc
