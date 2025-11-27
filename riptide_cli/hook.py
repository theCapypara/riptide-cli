from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal, Sequence

from click.exceptions import Exit
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from riptide.hook.additional_volumes import HookHostPathArgument
from riptide.hook.cli import HookCliDisplay
from riptide.hook.event import AnyHookEvent
from riptide.hook.manager import HookArgument
from riptide_cli.helpers import RiptideCliError, rule

if TYPE_CHECKING:
    from riptide_cli.loader import RiptideCliCtx


class RiptideCliHookDisplay(HookCliDisplay):
    prefix: str | None
    console: Console

    def __init__(self, console: Console):
        self.prefix = None
        self.console = console

    def will_run_hook(self, event_key: str, time: int):
        prefix = f"[cyan]{self.prefix}[/]: " if self.prefix else ""
        self.console.print(
            f"{prefix}Will run hooks in [bold]{time}[/] seconds. Hit [bold]CTRL-C[/] to skip running hooks", end=""
        )

    def will_run_hook_tick(self):
        self.console.print(".", end="")

    def after_will_run_hook(self):
        cols = os.get_terminal_size().columns
        print("\r" + " " * cols + "\r", end="")

    def system_info(self, msg: str):
        prefix = self.prefix or "Hook"
        self.console.print(f"[cyan]{prefix}[/]: " + escape(msg))

    def system_warn(self, msg: str):
        prefix = self.prefix or "Hook"
        self.console.print(Panel(escape(msg), title=f"{prefix} Warning", border_style="yellow", title_align="left"))

    def hook_execution_begin(self, event_key: str, name: str):
        prefix = f"{self.prefix}: " if self.prefix else ""
        rule(self.console, f"{prefix}Running [yellow]{event_key}[/] Hook: [cyan]{name}[/]...", style="cyan")

    def hook_execution_end(self, event_key: str, name: str, success: bool | Literal["warn"]):
        if success == "warn":
            self.console.print()  # Safety newline, since the command may not have output one
            rule(self.console, "Hook failed. Continuing...", style="yellow")
        elif not success:
            self.console.print()  # Safety newline, since the command may not have output one
            rule(self.console, "Hook failed.", style="red")
        else:
            rule(self.console, f"Hook [cyan]{name}[/] finished.", style="cyan")


def get_skip_hooks(ctx) -> bool:
    """Returns whether or not verbose mode is enabled"""
    if hasattr(ctx, "riptide_options"):
        return ctx.riptide_options["skip_hooks"]
    if hasattr(ctx, "parent"):
        if hasattr(ctx.parent, "riptide_options"):
            return ctx.parent.riptide_options["skip_hooks"]
    return True


def trigger_and_handle_hook(
    ctx: RiptideCliCtx,
    c_event: AnyHookEvent,
    arguments: Sequence[HookArgument],
    additional_host_mounts: dict[str, HookHostPathArgument] | None = None,  # container path -> host path + ro flag
    *,
    cli_hook_prefix: str | None = None,
    show_error_msg: bool = True,
):
    if get_skip_hooks(ctx):
        return
    if additional_host_mounts is None:
        additional_host_mounts = {}
    if isinstance(ctx.hook_manager.cli, RiptideCliHookDisplay):
        ctx.hook_manager.cli.prefix = cli_hook_prefix
    ret = ctx.hook_manager.trigger_event_on_cli(c_event, arguments, additional_host_mounts)
    if ret > 0:
        if show_error_msg:
            exc = RiptideCliError("A hook failed", ctx)
            exc.exit_code = ret
            raise exc
        raise Exit(ret)
