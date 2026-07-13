from __future__ import annotations

import pytest

from crewai_multiagent_demo.llm.model_registry import ModelRegistry, ModelSpec
from crewai_multiagent_demo.llm.provider import provider_for_model


def test_model_registry_resolves_alias() -> None:
    spec = ModelRegistry().resolve("flash")

    assert spec.model_name == "deepseek-v4-flash"
    assert spec.crewai_model == "deepseek/deepseek-v4-flash"


def test_model_registry_rejects_unknown_alias() -> None:
    with pytest.raises(ValueError, match="未知模型档位"):
        ModelRegistry().resolve("unknown")


def test_custom_registry_uses_its_first_model_as_default() -> None:
    registry = ModelRegistry({"custom": ModelSpec("custom", "model-x", "Custom", provider="openai")})

    assert registry.default_alias() == "custom"
    assert registry.resolve(None).crewai_model == "openai/model-x"


def test_deepseek_provider_defaults_are_explicit() -> None:
    provider = provider_for_model(ModelRegistry().resolve("flash"))

    assert provider.api_key_env_names == ("DEEPSEEK_API_KEY",)
    assert provider.request_timeout_seconds == 180.0


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="provider"):
        provider_for_model(ModelSpec("custom", "model", "Custom", provider="unknown"))
