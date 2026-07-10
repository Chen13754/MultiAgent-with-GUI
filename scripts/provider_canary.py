from __future__ import annotations

import os
from pathlib import Path

from crewai_multiagent_demo.config.loader import AppConfig
from crewai_multiagent_demo.core.runner import run_workflow
from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig


def main() -> int:
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_CANARY_API_KEY is required for tagged releases")
    root = Path(os.getenv("MULTIAGENT_HOME", ".cache/provider-canary")).resolve()
    result = run_workflow(
        topic="Reply with exactly: canary-ok",
        model_alias="flash",
        output_dir=root / "outputs",
        request_timeout_seconds=60,
        max_retries=1,
        app_config=AppConfig(
            agents=[
                AgentConfig(
                    id="canary",
                    role="Release canary",
                    goal="Return the requested release health response",
                    backstory="A minimal agent used only by the controlled release gate",
                )
            ],
            tasks=[
                TaskConfig(
                    id="canary",
                    name="Provider canary",
                    description="For {topic}, follow the instruction exactly and add nothing else.",
                    expected_output="The exact text canary-ok",
                    agent_id="canary",
                    artifact_role="full_report",
                )
            ],
        ),
    )
    if "canary-ok" not in result.full_report.lower():
        raise RuntimeError("Real-provider canary returned an unexpected response")
    print(f"Real-provider canary passed: {result.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
