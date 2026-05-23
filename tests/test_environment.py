from crewai_multiagent_demo.utils.environment import has_api_key, load_project_env, loaded_env_file


def test_load_project_env_prefers_explicit_env_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=from-test\n", encoding="utf-8")

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MULTIAGENT_ENV_FILE", str(env_file))

    assert load_project_env() == env_file
    assert loaded_env_file() == env_file
    assert has_api_key()

