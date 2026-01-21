from __future__ import annotations

import asyncio
import sys
from functools import update_wrapper
from typing import TYPE_CHECKING

import click
import rich
from click import ClickException
from rich.console import Console, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.style import Style
from rich.text import TextType
from riptide.engine.results import ResultQueue

if TYPE_CHECKING:
    from riptide_cli.loader import RiptideCliCtx


def get_is_verbose(ctx):
    """Returns whether or not verbose mode is enabled"""
    if hasattr(ctx, "riptide_options"):
        return ctx.riptide_options["verbose"]
    if hasattr(ctx, "parent"):
        if hasattr(ctx.parent, "riptide_options"):
            return ctx.parent.riptide_options["verbose"]
    return True


class RiptideCliError(ClickException):
    """Custom error class for displaying errors in the Riptide CLI"""

    ctx: RiptideCliCtx

    def __init__(self, message, ctx):
        super().__init__(message)
        self.ctx = ctx

    def show(self, file=None):
        if self.ctx.resilient_parsing:
            return
        verbose = get_is_verbose(self.ctx) or file is not None

        if file is None:
            file = sys.stderr
        if verbose:
            self.ctx.console.print_exception(show_locals=True, suppress=[click, asyncio])
        else:
            exception_message = escape(self.message)
            current_err: BaseException = self
            previous_message = str(self)
            while current_err.__context__ is not None:
                current_err = current_err.__context__
                # Filter duplicate exception messages. 'schema' used by configcrunch does that for example.
                if previous_message != str(current_err):
                    exception_message += f"\n[grey62]>> Caused by:[/] {escape(str(current_err))}"
                previous_message = str(current_err)

            rich.print(
                Panel(
                    exception_message,
                    title="Error",
                    subtitle="Use -v to show stack traces",
                    border_style="red",
                    title_align="left",
                    subtitle_align="left",
                ),
                file=file,
            )

    def __str__(self):
        error_string = self.__class__.__name__ + ": " + self.message
        if self.__cause__:
            error_string += ": " + self.__cause__.__class__.__name__ + ": " + str(self.__cause__)
        return error_string


def warn(console: Console, msg: RenderableType, boxed: bool = False):
    if isinstance(msg, str):
        msg = escape(msg)
    if boxed:
        console.print(Panel(msg, title="Warning", border_style="yellow", title_align="left"))
    else:
        console.print(f"[yellow][bold]Warning:[/bold] {msg}")


def rule(console: Console, title: TextType = "", *, characters: str = "─", style: str | Style = "rule.line"):
    if isinstance(title, str):
        title = "[default]" + title
    console.rule(f"[{style}]{characters}{characters} [/]{title}", style=style, align="left", characters=characters)


def cli_section(section):
    """
    Assigns commands to a section. Must be added as an annotation to commands,
    and therefor BEFORE the @click.command.
    :param section:
    :return:
    """

    def decorator(f):
        f.riptide_section = section
        return f

    return decorator


def async_command(interrupt_handler=lambda _, __: True):
    """
    Makes a Click command be wrapped inside the execution of an asyncio loop
    SOURCE:  https://github.com/pallets/click/issues/85
    """

    def decorator(f):
        def wrapper(ctx, *args, **kwargs):
            with asyncio.Runner() as runner:
                try:
                    return runner.run(f(ctx, *args, **kwargs))
                except (KeyboardInterrupt, SystemExit) as ex:
                    interrupt_handler(ctx, ex)

        return update_wrapper(wrapper, f)

    return decorator


def interrupt_handler(ctx, ex: KeyboardInterrupt | SystemExit):
    """Handle interrupts raised while running asynchronous AsyncIO code, fun stuff!"""
    # In case there are any open progress bars, close them:
    if hasattr(ctx, "live_display"):
        ctx.live_display.stop()
    if hasattr(ctx, "start_stop_errors"):
        from riptide_cli.lifecycle import display_errors

        display_errors(ctx.start_stop_errors, ctx)
    ctx.console.print(
        "[white on red]Riptide process was interrupted. Services might be in an invalid state. You may want to run riptide stop."
    )
    ctx.console.print("Finishing up... Stand by!")
    # Poison all ResultQueues to halt all start/stop threads after the next step.
    ResultQueue.poison()
    ctx.console.print("Done! If Riptide does not exit, hit CTRL+C.")
