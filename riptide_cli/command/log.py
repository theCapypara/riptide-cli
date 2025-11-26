import os
import sys
import time
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from random import Random
from threading import Thread
from typing import Sequence, cast

import click
from rich.console import Console
from rich.style import Style
from rich.text import Text
from riptide.config.document.service import Service
from riptide.config.service.logging import get_logging_path_for
from riptide_cli.command.project import cmd_constraint_project_set_up
from riptide_cli.helpers import cli_section
from riptide_cli.loader import RiptideCliCtx, load_riptide_core

STD_LOG_START_MARKER = "SERVICE RESTART -"


def load(main):
    """Adds the `log` command."""

    @cli_section("Service")
    @main.command()
    @click.pass_context
    @click.option(
        "--services", "-s", required=False, help="Limit the log output to one or more services (comma-seperated)."
    )
    @click.option(
        "--logs",
        "-l",
        required=False,
        help="Limit the log output to one or more log files (stdout, stderr, or any user defined logfile key; comma-seperated).",
    )
    @click.option("--follow", "-f", required=False, is_flag=True, help="Follow log output")
    @click.option(
        "--historic",
        "-h",
        required=False,
        is_flag=True,
        help="Show log output of previous service runs as well (only relevant for stdout, stderr).",
    )
    @click.option(
        "--show-names/--no-show-names",
        required=False,
        default=None,
        is_flag=True,
        help="Whether to show the service name and logfile key; by default on if TTY.",
    )
    def log(ctx, services: str, logs: str, follow: bool, historic: bool, show_names: bool | None):
        """
        Prints service logfiles and stdout/stderr.

        This command allows you to print the stdout, stderr or any user-defined
        log files from any of the configured services of this project.

        By default, all logfiles are printed.
        """
        ctx = cast(RiptideCliCtx, ctx)

        service_filter: list[str] = services.split(",") if services is not None else None
        logs_filter: list[str] = logs.split(",") if logs is not None else None

        if show_names is None:
            show_names = sys.stdin.isatty()

        load_riptide_core(ctx)
        cmd_constraint_project_set_up(ctx)

        project = ctx.system_config["project"]

        logfiles: list[tuple[str, str, str]] = []

        prefix_len = 0
        for service_key, service in project["app"]["services"].items():
            if service_filter is None or service_key in service_filter:
                if "logging" in service:
                    if "stdout" in service["logging"] and service["logging"]["stdout"]:
                        prefix_len = _add_log(prefix_len, logs_filter, service, service_key, "stdout", logfiles)
                    if "stderr" in service["logging"] and service["logging"]["stderr"]:
                        prefix_len = _add_log(prefix_len, logs_filter, service, service_key, "stderr", logfiles)
                    if "paths" in service["logging"]:
                        for name in service["logging"]["paths"].keys():
                            prefix_len = _add_log(prefix_len, logs_filter, service, service_key, name, logfiles)
                    if "commands" in service["logging"]:
                        for name in service["logging"]["commands"].keys():
                            prefix_len = _add_log(prefix_len, logs_filter, service, service_key, name, logfiles)

        queue: SimpleQueue[LineMsg] = SimpleQueue()
        printer = Printer(ctx.console, Console(stderr=True), prefix_len if show_names else None, queue)
        printer.start()

        logthreads = []
        for service_key, logkey, logfile in logfiles:
            logthread = Logwatcher(follow, historic, logfile, service_key, logkey, queue)
            logthreads.append(logthread)
            logthread.start()

        try:
            for t in logthreads:
                t.join()
            printer.poisoned = True
            printer.join()
        except KeyboardInterrupt:
            printer.poisoned = True
            for t in logthreads:
                t.poisoned = True
            printer.join(100)
            for t in logthreads:
                t.join()


def _add_log(
    prefix_len: int,
    logs_filter: Sequence[str] | None,
    service: Service,
    service_key: str,
    logkey: str,
    logfiles: list[tuple[str, str, str]],
):
    if logs_filter is None or logkey in logs_filter:
        logfiles.append((service_key, logkey, get_logging_path_for(service, logkey)))
        return max(prefix_len, len(f"{service_key} {logkey}"))
    return prefix_len


@dataclass(slots=True)
class LineMsg:
    log_prefix: str
    log_prefix_color: str
    msg: str
    is_err: bool


class Logwatcher(Thread):
    daemon = True

    poisoned: bool
    follow: bool
    historic: bool
    filepath: str
    service: str
    logkey: str
    msg_queue: SimpleQueue[LineMsg]

    def __init__(
        self, follow: bool, historic: bool, filepath: str, service: str, logkey: str, msg_queue: SimpleQueue[LineMsg]
    ):
        super().__init__()
        self.poisoned = False
        self.follow = follow
        self.historic = historic
        self.filepath = filepath
        self.service = service
        self.logkey = logkey
        self.msg_queue = msg_queue

    def run(self):
        try:
            prf = f"{self.service} {self.logkey}"
            prf_col = color_name(prf)

            with open(self.filepath, "r") as file:
                if self.follow:
                    # seek ~ 250 characters from the end of the file to print some of the last lines potentially
                    # I'm aware that this code is not unicode aware, but it's fine.
                    files_to_read_before_follow = os.path.getsize(self.filepath) - 250
                    read_characters = 0

                    while True:
                        newcount = len(file.readline())
                        read_characters += newcount
                        if newcount < 1 or read_characters >= files_to_read_before_follow:
                            break

                if not self.historic:
                    # Collect all current lines, and if we find any starting STD_LOG_START_MARKER, discard
                    # all lines before and including that
                    # If we go through all lines and don't find any STD_LOG_START_MARKER, just print all lines
                    collected_lines: list[str] = []
                    while True:
                        line = file.readline()
                        if line.startswith(STD_LOG_START_MARKER):
                            # Discard all lines collected so far, they can't be relevant
                            collected_lines = []
                        elif not line:
                            # EOF
                            for line in collected_lines:
                                self.msg_queue.put(
                                    LineMsg(log_prefix=prf, log_prefix_color=prf_col, msg=line.rstrip(), is_err=False)
                                )
                            break
                        else:
                            collected_lines.append(line)

                while True:
                    line = file.readline()
                    if not line:  # empty string
                        if not self.follow or self.poisoned:
                            break  # exit if we aren't following
                        time.sleep(0.1)
                        continue

                    # If self.historic, then mark restart messages
                    if (self.follow or self.historic) and line.startswith(STD_LOG_START_MARKER):
                        line = "\x1b[1;47;30m" + line
                    self.msg_queue.put(
                        LineMsg(log_prefix=prf, log_prefix_color=prf_col, msg=line.rstrip(), is_err=False)
                    )
        except Exception as exc:
            self.msg_queue.put(
                LineMsg(log_prefix=prf, log_prefix_color=prf_col, msg=f"{exc.__class__.__name__}: {exc}", is_err=True)
            )


class Printer(Thread):
    daemon = True

    poisoned: bool
    console_out: Console
    console_err: Console
    prefix_len: int | None
    msg_queue: SimpleQueue[LineMsg]

    def __init__(
        self, console_out: Console, console_err: Console, prefix_len: int | None, msg_queue: SimpleQueue[LineMsg]
    ):
        super().__init__()
        self.poisoned = False
        self.console_out = console_out
        self.console_err = console_err
        self.prefix_len = prefix_len
        self.msg_queue = msg_queue

    def run(self):
        while True:
            while True:
                try:
                    msg = self.msg_queue.get(True, 0.5)
                    break
                except Empty:
                    if self.poisoned:
                        return
            if msg.is_err:
                prefix = Text(f"{msg.log_prefix:<{self.prefix_len}}\x1b[0m", style=msg.log_prefix_color)
                self.console_err.print(prefix + Text(f"❌ Error: {msg.msg}", style=Style(color="white", bgcolor="red")))
            else:
                if self.prefix_len is not None:
                    prefix = Text(f"{msg.log_prefix:<{self.prefix_len}}| ", style=msg.log_prefix_color)
                    self.console_out.print(prefix, end="")
            self.console_out.print(Text.from_ansi(msg.msg), no_wrap=True, overflow="ignore", crop=False)


def color_name(text: str) -> str:
    rand = Random(text)
    return rand.choice(
        [
            "red",
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
            "bright_red",
            "bright_green",
            "bright_yellow",
            "bright_blue",
            "bright_magenta",
            "bright_cyan",
        ]
    )
