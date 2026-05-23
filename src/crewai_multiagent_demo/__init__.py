"""CrewAI multi-agent demo application package."""

from crewai_multiagent_demo.core.runner import DEFAULT_TOPIC, run_workflow
from crewai_multiagent_demo.domain.run_result import RunResult

__all__ = ["DEFAULT_TOPIC", "RunResult", "run_workflow"]
