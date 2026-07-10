from __future__ import annotations

from scripts import build_gui


def test_target_name_maps_native_platform_and_architecture(monkeypatch) -> None:
    monkeypatch.setattr(build_gui.platform, "system", lambda: "Windows")
    monkeypatch.setattr(build_gui.platform, "machine", lambda: "AMD64")
    assert build_gui.target_name() == "windows-x64"

    monkeypatch.setattr(build_gui.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(build_gui.platform, "machine", lambda: "arm64")
    assert build_gui.target_name() == "macos-arm64"


def test_pnpm_command_supports_project_runtime_override(monkeypatch) -> None:
    monkeypatch.setenv("PNPM_NODE", "project-node")
    monkeypatch.setenv("PNPM_SCRIPT", "project-pnpm.cjs")

    assert build_gui.pnpm_command() == ["project-node", "project-pnpm.cjs"]


def test_check_mode_parses_without_starting_a_build() -> None:
    assert build_gui.parse_args(["--check"]).check is True
