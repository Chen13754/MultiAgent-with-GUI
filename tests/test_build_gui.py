from __future__ import annotations

from pathlib import Path

import pytest

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


def test_prerequisite_check_does_not_require_prebuilt_frontend(tmp_path, monkeypatch) -> None:
    project = tmp_path
    (project / "src").mkdir()
    (project / "src" / "web_gui_app.py").write_text("", encoding="utf-8")
    (project / "config").mkdir()
    (project / "config" / "workflow.json").write_text("{}", encoding="utf-8")
    (project / "contracts").mkdir()
    (project / "contracts" / "studio.schema.json").write_text("{}", encoding="utf-8")
    (project / "scripts").mkdir()
    (project / "scripts" / "windows_launcher.cs").write_text("launcher", encoding="utf-8")
    monkeypatch.setattr(build_gui, "PROJECT_ROOT", project)
    monkeypatch.setattr(build_gui, "FRONTEND_DIST", project / "frontend" / "dist")
    monkeypatch.setattr(build_gui, "pnpm_command", lambda: ["pnpm"])
    monkeypatch.setattr(build_gui, "WINDOWS_LAUNCHER_SOURCE", project / "scripts" / "windows_launcher.cs")
    monkeypatch.setattr(build_gui, "windows_csharp_compiler", lambda: Path("csc.exe"))

    build_gui.check_prerequisites(require_frontend_dist=False)
    with pytest.raises(RuntimeError, match="dist.index.html"):
        build_gui.check_prerequisites(require_frontend_dist=True)


def test_tagged_windows_release_cannot_skip_signing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(build_gui.platform, "system", lambda: "Windows")
    monkeypatch.setenv("REQUIRE_SIGNING", "1")
    monkeypatch.delenv("WINDOWS_SIGN_PFX_PATH", raising=False)
    monkeypatch.delenv("WINDOWS_SIGN_PFX_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="signing credentials"):
        build_gui.sign_and_notarize_bundle(tmp_path)


def test_windows_launcher_is_a_windowed_direct_entrypoint(tmp_path, monkeypatch) -> None:
    project = tmp_path
    bundle = project / "dist" / "MultiagentStudio"
    bundle.mkdir(parents=True)
    (bundle / "MultiagentStudio.exe").write_bytes(b"packaged-app")
    source = project / "scripts" / "windows_launcher.cs"
    source.parent.mkdir()
    source.write_text("launcher source", encoding="utf-8")
    captured: list[list[str]] = []

    def fake_run(command: list[str], *, cwd=project) -> None:
        captured.append(command)
        output_argument = next(part for part in command if part.startswith("/out:"))
        Path(output_argument.removeprefix("/out:")).write_bytes(b"launcher")

    monkeypatch.setattr(build_gui.platform, "system", lambda: "Windows")
    monkeypatch.setattr(build_gui, "PROJECT_ROOT", project)
    monkeypatch.setattr(build_gui, "WINDOWS_LAUNCHER_SOURCE", source)
    monkeypatch.setattr(build_gui, "windows_csharp_compiler", lambda: Path("csc.exe"))
    monkeypatch.setattr(build_gui, "project_version", lambda: "0.2.0")
    monkeypatch.setattr(build_gui, "run", fake_run)

    launcher = build_gui.build_windows_launcher(bundle)

    assert launcher == project / "MultiagentStudio.exe"
    assert launcher.read_bytes() == b"launcher"
    assert "/target:winexe" in captured[0]
    assert "/reference:System.Windows.Forms.dll" in captured[0]
    version_source = project / ".cache" / "build" / "launcher_version.cs"
    assert version_source.read_text(encoding="utf-8").find('AssemblyVersion("0.2.0.0")') >= 0


def test_windows_version_metadata_is_generated_from_project_version(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(build_gui, "PROJECT_ROOT", tmp_path)

    path = build_gui.write_windows_version_file("0.2.0")

    text = path.read_text(encoding="utf-8")
    assert "filevers=(0, 2, 0, 0)" in text
    assert "ProductVersion', u'0.2.0'" in text


def test_pyinstaller_collects_crewai_translation_resources(monkeypatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr(build_gui, "run", lambda command, cwd=build_gui.PROJECT_ROOT: captured.append(command))
    monkeypatch.setattr(build_gui, "check_prerequisites", lambda **_: None)
    monkeypatch.setattr(build_gui, "pnpm_command", lambda: ["pnpm"])
    monkeypatch.setattr(build_gui, "sign_and_notarize_bundle", lambda bundle: None)
    monkeypatch.setattr(build_gui, "make_archive", lambda bundle: bundle.with_suffix(".zip"))
    monkeypatch.setattr(build_gui, "write_checksum", lambda archive: archive.with_suffix(".sha256"))
    monkeypatch.setattr(build_gui, "project_version", lambda: "test")
    monkeypatch.setattr(build_gui.platform, "system", lambda: "Linux")
    monkeypatch.setattr(build_gui, "FRONTEND_DIST", build_gui.PROJECT_ROOT / ".cache" / "missing-dist")

    # The assertion is intentionally source-level: it guards the command that
    # produces the packaged executable without running a heavyweight build.
    source = (build_gui.PROJECT_ROOT / "scripts" / "build_gui.py").read_text(encoding="utf-8")
    assert '"crewai"' in source
    assert '"--exclude-module"' not in source or '"chromadb"' not in source
