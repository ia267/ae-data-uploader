"""Shell tab-completion setup for ae-upload."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click
from click.shell_completion import get_completion_class

from .config import user_config_dir
from .ui import UI


PROG_NAME = "ae-upload"
COMPLETE_VAR = "_AE_UPLOAD_COMPLETE"
SUPPORTED_SHELLS = ("bash", "zsh", "fish")
RC_MARKER = "# ae-upload shell completion"


@dataclass(frozen=True)
class CompletionInstallResult:
    """Describe what installing completion changed."""

    shell: str
    script_path: Path
    rc_path: Optional[Path]
    rc_updated: bool


def detect_shell() -> Optional[str]:
    """Return the user's login shell name if it is supported, else None."""
    shell = Path(os.environ.get("SHELL", "")).name
    return shell if shell in SUPPORTED_SHELLS else None


def completion_script(cli: click.Command, shell: str) -> str:
    """Return the completion script Click generates for ``shell``."""
    completion_class = get_completion_class(shell)
    if completion_class is None:
        raise ValueError(f"Unsupported shell: {shell}")
    return completion_class(cli, {}, PROG_NAME, COMPLETE_VAR).source()


def _fish_completions_dir() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / "fish" / "completions"


def _rc_snippet(shell: str, script_path: Path) -> str:
    lines = [RC_MARKER]
    if shell == "zsh":
        # Click's zsh script calls compdef, which needs compinit loaded.
        lines.append("(( $+functions[compdef] )) || { autoload -Uz compinit && compinit }")
    lines.append(f'[ -f "{script_path}" ] && source "{script_path}"')
    return "\n".join(lines) + "\n"


def is_completion_installed(shell: str) -> bool:
    """Return True if completion for ``shell`` has already been set up."""
    if shell == "fish":
        return (_fish_completions_dir() / f"{PROG_NAME}.fish").exists()
    rc_path = Path.home() / f".{shell}rc"
    try:
        return RC_MARKER in rc_path.read_text(encoding="utf-8")
    except OSError:
        return False


def install_completion(cli: click.Command, shell: str) -> CompletionInstallResult:
    """
    Install tab completion for ``shell``.

    The script is generated once and saved to a file, so new shells source a
    static file instead of starting Python on every launch. For bash and zsh a
    marked ``source`` line is added to ``~/.bashrc`` / ``~/.zshrc`` (only once);
    fish loads files from its completions directory automatically.
    """
    script = completion_script(cli, shell)

    if shell == "fish":
        script_path = _fish_completions_dir() / f"{PROG_NAME}.fish"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script, encoding="utf-8")
        return CompletionInstallResult(shell, script_path, None, False)

    script_path = user_config_dir() / "completion" / f"{PROG_NAME}.{shell}"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")

    rc_path = Path.home() / f".{shell}rc"
    existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
    if RC_MARKER in existing:
        return CompletionInstallResult(shell, script_path, rc_path, False)

    prefix = "" if not existing or existing.endswith("\n") else "\n"
    with open(rc_path, "a", encoding="utf-8") as f:
        f.write(f"{prefix}\n{_rc_snippet(shell, script_path)}")
    return CompletionInstallResult(shell, script_path, rc_path, True)


def echo_install_result(result: CompletionInstallResult) -> None:
    """Print what install_completion() did and how to start using it."""
    ui = UI()
    ui.ok(f"Tab completion script saved to {result.script_path}")
    if result.rc_updated:
        ui.ok(f"Added completion setup to {result.rc_path}")
    elif result.rc_path:
        ui.ok(f"{result.rc_path} already loads ae-upload completion")
    if result.shell == "fish":
        ui.detail("Open a new terminal to start using it.")
    else:
        ui.detail(f"Open a new terminal (or run: source {result.rc_path}) to start using it.")
