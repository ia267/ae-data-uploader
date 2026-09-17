from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from ae_uploader.cli import cli
from ae_uploader.completion import RC_MARKER


def _fake_home(monkeypatch, tmp_path: Path, shell: str) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SHELL", f"/bin/{shell}")
    monkeypatch.setenv("AE_UPLOAD_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return home


def test_completion_prints_script_for_requested_shell():
    result = CliRunner().invoke(cli, ["completion", "bash"])

    assert result.exit_code == 0
    assert "_AE_UPLOAD_COMPLETE" in result.output
    assert "complete " in result.output


def test_completion_install_bash_is_idempotent(tmp_path, monkeypatch):
    home = _fake_home(monkeypatch, tmp_path, "bash")
    (home / ".bashrc").write_text("export FOO=1", encoding="utf-8")
    runner = CliRunner()

    first = runner.invoke(cli, ["completion", "--install"])
    second = runner.invoke(cli, ["completion", "--install"])

    assert first.exit_code == 0 and second.exit_code == 0
    rc = (home / ".bashrc").read_text(encoding="utf-8")
    assert rc.startswith("export FOO=1\n")
    assert rc.count(RC_MARKER) == 1
    script = tmp_path / "config" / "completion" / "ae-upload.bash"
    assert script.exists()
    assert str(script) in rc


def test_completion_install_zsh_loads_compinit(tmp_path, monkeypatch):
    home = _fake_home(monkeypatch, tmp_path, "zsh")

    result = CliRunner().invoke(cli, ["completion", "--install"])

    assert result.exit_code == 0
    assert "compinit" in (home / ".zshrc").read_text(encoding="utf-8")


def test_completion_install_fish_writes_completions_file(tmp_path, monkeypatch):
    home = _fake_home(monkeypatch, tmp_path, "fish")

    result = CliRunner().invoke(cli, ["completion", "--install"])

    assert result.exit_code == 0
    assert (home / ".config" / "fish" / "completions" / "ae-upload.fish").exists()


def test_completion_fails_for_unsupported_shell(tmp_path, monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/tcsh")

    result = CliRunner().invoke(cli, ["completion"])

    assert result.exit_code == 1
    assert "Could not detect a supported shell" in result.output


def test_completion_suggests_subcommands(monkeypatch):
    monkeypatch.setenv("COMP_WORDS", "ae-upload comp")
    monkeypatch.setenv("COMP_CWORD", "1")
    monkeypatch.setenv("_AE_UPLOAD_COMPLETE", "bash_complete")

    result = CliRunner().invoke(cli, [], prog_name="ae-upload")

    assert "plain,completion" in result.output
