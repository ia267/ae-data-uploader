"""Interactive prompt helpers for ae-upload."""

from __future__ import annotations

import os
import sys

import click


def _read_masked(prompt: str, mask: str) -> str:
    """Read a line from the terminal, echoing ``mask`` for each character."""
    click.echo(prompt, nl=False)
    chars = []

    if os.name == "nt":
        import msvcrt

        def getch() -> str:
            return msvcrt.getwch()

        def cleanup() -> None:
            pass
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        # cbreak disables echo but keeps ISIG, so Ctrl-C still interrupts.
        tty.setcbreak(fd)

        def getch() -> str:
            return sys.stdin.read(1)

        def cleanup() -> None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    try:
        while True:
            ch = getch()
            if ch in ("\r", "\n", ""):
                break
            if ch == "\x03":  # Ctrl-C on Windows
                raise KeyboardInterrupt
            if ch == "\x04" and not chars:  # Ctrl-D on empty input
                raise EOFError
            if ch in ("\x7f", "\x08"):  # Backspace
                if chars:
                    chars.pop()
                    click.echo("\b \b", nl=False)
                continue
            if ch in ("\x00", "\xe0"):  # Windows special-key prefix
                getch()
                continue
            if ch == "\x1b":
                # Skip escape sequences (arrow keys, bracketed paste markers).
                if getch() == "[":
                    while True:
                        seq_ch = getch()
                        if not seq_ch or seq_ch.isalpha() or seq_ch == "~":
                            break
                continue
            if not ch.isprintable():
                continue
            chars.append(ch)
            click.echo(mask, nl=False)
    finally:
        cleanup()
        click.echo()

    return "".join(chars).strip()


def prompt_secret(prompt: str, mask: str = "*") -> str:
    """
    Prompt for a secret (e.g. an access token), showing ``mask`` per character.

    Unlike ``click.prompt(hide_input=True)``, users can see that typed or
    pasted input was received. Falls back to click's hidden prompt when stdin
    is not an interactive terminal (pipes, tests, CI).
    """
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    while True:
        if interactive:
            try:
                value = _read_masked(f"{prompt}: ", mask)
            except (KeyboardInterrupt, EOFError):
                raise click.Abort()
        else:
            value = click.prompt(prompt, type=str, hide_input=True).strip()
        if value:
            return value
        click.echo("[ERROR] A value is required.", err=True)
