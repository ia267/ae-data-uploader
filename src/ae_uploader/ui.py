"""
Terminal output helpers for ae-upload.

In an interactive terminal, messages use colour and symbols, slow steps show a
spinner and uploads show progress bars. When output is redirected (pipes, CI,
log files, tests) the same messages are printed as plain ``[OK]``/``[INFO]``
lines so they stay easy to read and grep.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

import click
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table


def format_bytes(size: float) -> str:
    """Format bytes to a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


class UI:
    """Print status messages, summaries and progress for one command run."""

    def __init__(self) -> None:
        # Consoles resolve sys.stdout/sys.stderr when writing, so this also
        # works when click's test runner swaps the streams.
        self.out = Console(highlight=False)
        self.err = Console(stderr=True, highlight=False)

    @property
    def rich(self) -> bool:
        return self.out.is_terminal

    def _plain(self, tag: str, message: str, err: bool = False) -> None:
        click.echo(f"[{tag}] {message}", err=err)

    def blank(self) -> None:
        click.echo()

    def info(self, message: str) -> None:
        if self.rich:
            self.out.print(f"[cyan]›[/] {escape(message)}")
        else:
            self._plain("INFO", message)

    def ok(self, message: str) -> None:
        if self.rich:
            self.out.print(f"[green]✓[/] {escape(message)}")
        else:
            self._plain("OK", message)

    def warn(self, message: str) -> None:
        if self.err.is_terminal:
            self.err.print(f"[yellow]![/] [yellow]{escape(message)}[/]")
        else:
            self._plain("WARNING", message, err=True)

    def error(self, message: str) -> None:
        if self.err.is_terminal:
            self.err.print(f"[bold red]✗[/] [red]{escape(message)}[/]")
        else:
            self._plain("ERROR", message, err=True)

    def detail(self, message: str, err: bool = False) -> None:
        """Print an indented follow-up line for the previous message."""
        console = self.err if err else self.out
        if console.is_terminal:
            console.print(f"  [dim]{escape(message)}[/]")
        else:
            click.echo(f"   {message}", err=err)

    @contextlib.contextmanager
    def status(self, message: str) -> Iterator[None]:
        """Show a spinner while a slow step runs."""
        if self.rich:
            with self.out.status(escape(message), spinner="dots"):
                yield
        else:
            self._plain("INFO", message)
            yield

    def summary(self, title: str, rows: Sequence[Tuple[str, str]]) -> None:
        """Print a labelled summary box (plain ``label: value`` lines when redirected)."""
        if self.rich:
            table = Table.grid(padding=(0, 2))
            table.add_column(style="bold")
            table.add_column()
            for label, value in rows:
                table.add_row(label, escape(value))
            self.out.print(Panel(table, title=f"[bold]{escape(title)}[/]",
                                 title_align="left", expand=False))
        else:
            self._plain("INFO", title)
            for label, value in rows:
                click.echo(f"   {label}: {value}")

    def link(self, label: str, url: str) -> None:
        if self.rich:
            self.out.print(f"  {escape(label)} [link={url}]{escape(url)}[/link]")
        else:
            click.echo(f"   {label} {url}")

    def upload_progress(self, files: List[Path], root: Optional[Path] = None) -> "UploadProgress":
        return UploadProgress(self, files, root)


class UploadProgress:
    """
    Progress display for uploading one or more files.

    Use as a context manager, then pass :meth:`start_file` as the per-file
    callback and :meth:`advance` as the per-chunk bytes callback.
    """

    def __init__(self, ui: UI, files: List[Path], root: Optional[Path] = None):
        self.ui = ui
        self.files = files
        self.root = root
        self._progress: Optional[Progress] = None
        self._total_task: Optional[TaskID] = None
        self._file_task: Optional[TaskID] = None
        self._file_label = ""
        self._file_size: Optional[int] = None

    def __enter__(self) -> "UploadProgress":
        if self.ui.rich:
            self._progress = Progress(
                TextColumn("  {task.description}", markup=True),
                BarColumn(bar_width=30),
                TextColumn("{task.percentage:>3.0f}%"),
                DownloadColumn(binary_units=True),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=self.ui.out,
            )
            self._progress.__enter__()
            if len(self.files) > 1:
                total = sum(f.stat().st_size for f in self.files)
                self._total_task = self._progress.add_task("[bold]Total[/]", total=total)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._progress is None:
            return
        if exc_type is None:
            self._finish_file()
        elif self._file_task is not None:
            self._progress.remove_task(self._file_task)
        self._progress.__exit__(exc_type, exc, tb)

    def _label(self, file_path: Path) -> str:
        if self.root is not None:
            try:
                return file_path.relative_to(self.root).as_posix()
            except ValueError:
                pass
        return file_path.name

    def _finish_file(self) -> None:
        if self._progress is None or self._file_task is None:
            return
        self._progress.remove_task(self._file_task)
        self._progress.console.print(
            f"  [green]✓[/] {escape(self._file_label)} "
            f"[dim]({format_bytes(self._file_size or 0)})[/]"
        )
        self._file_task = None

    def start_file(self, file_path: Path, index: int, total: int) -> None:
        """Call before each file upload starts."""
        label = self._label(file_path)
        size = file_path.stat().st_size
        if self._progress is None:
            renamed = f" as {file_path.name}" if label != file_path.name else ""
            click.echo(f"   [{index}/{total}] Uploading {label}{renamed} ({format_bytes(size)})")
            return
        self._finish_file()
        self._file_label = label
        self._file_size = size
        self._file_task = self._progress.add_task(escape(label), total=size)

    def start_archive(self, name: str) -> None:
        """Show an indeterminate bar while a zip archive is being built."""
        self._file_label = name
        self._file_size = None
        if self._progress is not None:
            self._file_task = self._progress.add_task(
                f"Creating {escape(name)}", total=None
            )

    def advance(self, chunk: int, file_size: int) -> None:
        """Bytes callback for :meth:`InvenioClient.upload_file`."""
        if self._progress is None:
            return
        if self._file_task is None:
            self._file_task = self._progress.add_task(escape(self._file_label), total=file_size)
            self._file_size = file_size
        elif self._file_size is None:
            # Archive finished building; upload has started.
            self._file_size = file_size
            self._progress.update(
                self._file_task, description=escape(self._file_label), total=file_size
            )
        self._progress.advance(self._file_task, chunk)
        if self._total_task is not None:
            self._progress.advance(self._total_task, chunk)
