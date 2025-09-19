from typing import IO, Any, Sequence, cast

import click
from click import ClickException, echo, style
from riptide.hook.event import HookEvent
from riptide.hook.manager import ApplicableEventConfiguration
from riptide_cli.command.constants import (
    CMD_HOOK_CONFIGURE,
    CMD_HOOK_LIST,
    CMD_HOOK_TRIGGER,
)
from riptide_cli.helpers import TAB, RiptideCliError, cli_section, warn
from riptide_cli.loader import RiptideCliCtx, load_riptide_core
from setproctitle import setproctitle


class EmptyClickException(ClickException):
    def __init__(self, exit_code: int) -> None:
        self.exit_code = exit_code
        super().__init__("")

    def show(self, file: IO[Any] | None = None) -> None:
        pass


def load(main):
    """Adds all hook commands to the CLI"""

    @cli_section("Hook")
    @main.command(CMD_HOOK_LIST)
    @click.option(
        "--default",
        "-g",
        required=False,
        is_flag=True,
        help="Show the global default configuration.",
    )
    @click.option(
        "--all",
        "-a",
        required=False,
        is_flag=True,
        help="Also list events that currently have no hooks defined.",
    )
    @click.pass_context
    def configuration(ctx, all: bool, default: bool):
        """List currently registered hooks and their current configuration."""
        ctx = cast(RiptideCliCtx, ctx)
        load_riptide_core(ctx, skip_project_load=default)
        assert ctx.system_config is not None

        (defaults, events) = ctx.hook_manager.get_current_configuration()
        events = sorted(events, key=lambda e: HookEvent.key_for(e["event"]))

        echo(style("[Default]:", bold=True))
        print_hook_status(defaults, not default, None)

        for event in events:
            if all or len(event["hooks"]) > 0:
                key = HookEvent.key_for(event["event"])
                echo("")
                echo(f"{key}:")
                print_hook_status(event, not default, defaults)
                print(TAB + "Hooks:")
                if len(event["hooks"]) <= 0:
                    print(TAB + TAB + "None")
                for hook in event["hooks"]:
                    from_global_suffix = " (from global)" if hook["defined_in"] == "default" else ""
                    print(TAB + TAB + f"- {hook['key']}{from_global_suffix}")

    @cli_section("Hook")
    @main.command(CMD_HOOK_CONFIGURE)
    @click.option(
        "--default",
        "-g",
        required=False,
        is_flag=True,
        help="Configure the global default instead of the currently loaded project.",
    )
    @click.option("--enable", required=False, type=bool, help="Enable or disable event")
    @click.option(
        "--wait-time",
        required=False,
        type=int,
        help="Configure the wait time. Riptide will wait for this amount of time before running hooks and allows you to interrupt. Set to 0 to disable.",
    )
    @click.argument("event_name", required=False)
    @click.pass_context
    def configure(ctx, default: bool, event_name: str | None, enable: int | None, wait_time: int | None):
        """
        Configure hooks. This can be done on a per-event basis, or you can change the global defaults. Likewise, you
        can change the settings for this project or the default across all projects.

        Hooks for events can be disabled or enabled and wait times can be configured.

        Examples:

           Enable hooks globally:

               riptide hook-configure -g --enable=true

           Disable hooks for the current project (overrides global setting):

               riptide hook-configure --enable=false

           Enable git-pre-commit hooks globally (overrides global and default project setting):

               riptide hook-configure -g --enable=false git-pre-commit

           Disable git-pre-commit hooks for the current project (overrides any other setting):

               riptide hook-configure --enable=false git-pre-commit

        """
        ctx = cast(RiptideCliCtx, ctx)
        load_riptide_core(ctx, skip_project_load=default)
        assert ctx.system_config is not None

        if not default and "project" not in ctx.system_config:
            warn("No project is loaded, using global default instead.")
            default = True

        c_event = None
        if event_name:
            c_event = HookEvent.validate(event_name)
            if not c_event:
                raise RiptideCliError(f"Invalid hook name {event_name}", ctx)

        if enable is None and wait_time is None:
            raise RiptideCliError("Please specify either --enable, --wait-time or both.", ctx)

        ctx.hook_manager.configure_event(c_event, default, enable, wait_time)

        (defaults, events) = ctx.hook_manager.get_current_configuration()

        if event_name:
            echo("Event configured:")
            event = next(event for event in events if event["event"] == c_event)
            print_hook_status(event, not default, defaults)
        else:
            echo("Default configured:")
            print_hook_status(defaults, not default, None)

    @cli_section("Hook")
    @main.command(CMD_HOOK_TRIGGER)
    @click.argument("event", required=True)
    @click.argument("arguments", required=False, nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def trigger(ctx, event: str, arguments: Sequence[str]):
        """Trigger an event and all its hooks (if enabled). All additional arguments are passed to the hooks."""
        ctx = cast(RiptideCliCtx, ctx)
        load_riptide_core(ctx, False)
        assert ctx.system_config is not None

        c_event = HookEvent.validate(event)
        if not c_event:
            raise RiptideCliError(f"Invalid hook name {event}", ctx)

        try:
            setproctitle("riptide-hook-trigger")
        except:
            pass
        ret = ctx.hook_manager.trigger_event_on_cli(c_event, arguments)
        if ret != 0:
            raise EmptyClickException(ret)


def print_hook_status(
    config: ApplicableEventConfiguration,
    project_is_loaded: bool,
    compare_against_defaults: ApplicableEventConfiguration | None,
):
    if config["enabled"]["effective"]:
        enable_value = style("yes", fg="green")
    else:
        enable_value = style("no", fg="red")
    if config["enabled"]["default"] is None and config["enabled"]["project"] is None:
        if compare_against_defaults is not None:
            enable_value += " (from default)"
        else:
            enable_value += " (not set)"
    elif config["enabled"]["project"] is None and project_is_loaded:
        enable_value += " (from global)"
    echo(TAB + "enabled: " + enable_value)

    if config["wait_time"]["effective"] > 0:
        wait_time_value = f"{config['wait_time']['effective']}s"
    else:
        wait_time_value = "none"
    if config["wait_time"]["default"] is None and config["wait_time"]["project"] is None:
        wait_time_value += " (not set)"
    elif config["wait_time"]["project"] is None and project_is_loaded:
        wait_time_value += " (global)"
    echo(TAB + "wait time: " + wait_time_value)
