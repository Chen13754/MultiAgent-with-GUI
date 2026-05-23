from __future__ import annotations

from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY, ModelRegistry, ModelSpec


def resolve_model(alias: str | None, registry: ModelRegistry = MODEL_REGISTRY) -> ModelSpec:
    return registry.resolve(alias)
