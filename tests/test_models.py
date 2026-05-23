from __future__ import annotations

import pytest

from crewai_multiagent_demo.llm.model_registry import ModelRegistry


def test_model_registry_resolves_alias() -> None:
    spec = ModelRegistry().resolve("flash")

    assert spec.model_name == "deepseek-v4-flash"
    assert spec.crewai_model == "deepseek/deepseek-v4-flash"


def test_model_registry_rejects_unknown_alias() -> None:
    with pytest.raises(ValueError, match="未知模型档位"):
        ModelRegistry().resolve("unknown")
