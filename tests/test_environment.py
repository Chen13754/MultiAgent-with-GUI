import os
from pathlib import Path

from crewai_multiagent_demo.utils.environment import (
    candidate_env_files,
    has_api_key,
    has_api_key_for_model,
    load_project_env,
    loaded_env_file,
    require_api_key,
)
from crewai_multiagent_demo.utils.paths import _frozen_project_root


def test_load_project_env_prefers_explicit_env_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=from-test\n", encoding="utf-8")

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MULTIAGENT_ENV_FILE", str(env_file))

    assert load_project_env() == env_file
    assert loaded_env_file() == env_file
    assert has_api_key()


def test_env_file_does_not_clear_injected_secret_and_storage_is_absolute(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=\nCREWAI_STORAGE_DIR=.cache/crewai\n", encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "managed-secret")
    monkeypatch.setenv("MULTIAGENT_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("CREWAI_STORAGE_DIR", raising=False)

    load_project_env(env_file)

    assert os.environ["DEEPSEEK_API_KEY"] == "managed-secret"
    assert Path(os.environ["CREWAI_STORAGE_DIR"]).is_absolute()
    assert Path(os.environ["CREWAI_STORAGE_DIR"]).is_relative_to(tmp_path)


def test_candidate_env_files_includes_project_root(monkeypatch) -> None:
    monkeypatch.delenv("MULTIAGENT_ENV_FILE", raising=False)
    monkeypatch.delenv("MULTIAGENT_PROJECT_ROOT", raising=False)

    candidates = candidate_env_files()

    assert any(path.name == ".env" for path in candidates)


def test_deepseek_model_requires_deepseek_api_key(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    assert has_api_key()
    assert not has_api_key_for_model("deepseek/deepseek-v4-flash")

    try:
        require_api_key("deepseek/deepseek-v4-flash")
    except RuntimeError as exc:
        assert "DEEPSEEK_API_KEY" in str(exc)
    else:
        raise AssertionError("DeepSeek model should require DEEPSEEK_API_KEY")


def test_frozen_project_root_for_root_exe(tmp_path) -> None:
    exe = tmp_path / "MultiagentStudio.exe"

    assert _frozen_project_root(exe) == tmp_path


def test_frozen_project_root_for_dist_exe(tmp_path) -> None:
    exe = tmp_path / "dist" / "MultiagentStudio" / "MultiagentStudio.exe"

    assert _frozen_project_root(exe) == tmp_path
