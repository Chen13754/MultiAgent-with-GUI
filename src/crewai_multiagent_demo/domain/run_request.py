from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RunRequest:
    run_id: str
    topic: str
    model_alias: str
    config_dir: Path
    output_dir: Path
    env_file: Path | None = None
    request_timeout_seconds: float = 180.0
    total_timeout_seconds: float = 1200.0
    max_retries: int = 2

    @classmethod
    def create(
        cls,
        *,
        topic: str,
        model_alias: str,
        config_dir: str | Path,
        output_dir: str | Path,
        env_file: str | Path | None = None,
    ) -> RunRequest:
        return cls(
            run_id=uuid4().hex,
            topic=topic,
            model_alias=model_alias,
            config_dir=Path(config_dir),
            output_dir=Path(output_dir),
            env_file=Path(env_file) if env_file is not None else None,
        )
