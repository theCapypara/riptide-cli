import os.path
from typing import cast

import click
from rich.tree import Tree
from riptide.hook.additional_volumes import HookHostPathArgument
from riptide.hook.event import HookEvent
from riptide.hook.manager import ApplicableEventConfiguration, HookArgument
from riptide_cli.command.constants import (
    CMD_HOOK_CONFIGURE,
    CMD_HOOK_LIST,
    CMD_HOOK_TRIGGER,
)
from riptide_cli.helpers import RiptideCliError, cli_section, warn
from riptide_cli.hook import trigger_and_handle_hook
from riptide_cli.loader import RiptideCliCtx, load_riptide_core
from setproctitle import setproctitle


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

        hook_tree = Tree("Event Configuration")
        default_branch = hook_tree.add("<Default>")
        add_hook_status(default_branch, defaults, not default, None)

        for event in events:
            if all or len(event["hooks"]) > 0:
                key = HookEvent.key_for(event["event"])
                event_branch = hook_tree.add(key)
                add_hook_status(event_branch, event, not default, defaults)
                hooks_branch = event_branch.add("Hooks:")
                if len(event["hooks"]) <= 0:
                    hooks_branch.add("None")
                for hook in event["hooks"]:
                    from_global_suffix = " (from global)" if hook["defined_in"] == "default" else ""
                    hooks_branch.add(f"{hook['key']}{from_global_suffix}")

        ctx.console.print(hook_tree)

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
            warn(ctx.console, "No project is loaded, using global default instead.")
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
            try:
                tree = Tree(f"Event {event_name} configured:")
                event = next(event for event in events if event["event"] == c_event)
                add_hook_status(tree, event, not default, defaults)
            except StopIteration:
                raise RiptideCliError("No such event is defined for this project", ctx)
        else:
            tree = Tree("Default configured:")
            add_hook_status(tree, defaults, not default, None)
        ctx.console.print(tree)

    @cli_section("Hook")
    @main.command(
        CMD_HOOK_TRIGGER,
        context_settings={
            "ignore_unknown_options": True  # Make all unknown options redirect to arguments
        },
    )
    @click.option(
        "--mount-host-paths",
        "-m",
        required=False,
        is_flag=True,
        help="If set, any passed argument that looks like an absolute or relative path is mounted into command containers.",
    )
    @click.argument("event", required=True)
    @click.argument("arguments", required=False, nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def trigger(ctx, mount_host_paths: bool, event: str, arguments: list[str]):
        """Trigger an event and all its hooks (if enabled). All additional arguments are passed to the hooks."""
        ctx = cast(RiptideCliCtx, ctx)
        load_riptide_core(ctx, False)
        assert ctx.system_config is not None

        c_event = HookEvent.validate(event)
        if not c_event:
            raise RiptideCliError(f"Invalid hook name {event}", ctx)

        try:
            setproctitle("riptide-hook-trigger")
        except Exception:
            pass

        if mount_host_paths:
            new_arguments: list[HookArgument] = []
            for arg in arguments:
                if arg.startswith("/") or arg.startswith("./"):
                    try:
                        if os.path.exists(arg):
                            new_arguments.append(HookHostPathArgument(arg))
                    except OSError:
                        pass
                new_arguments.append(arg)
        else:
            new_arguments = arguments  # type: ignore

        trigger_and_handle_hook(ctx, c_event, new_arguments, show_error_msg=False, cli_hook_prefix="Riptide")


def add_hook_status(
    tree: Tree,
    config: ApplicableEventConfiguration,
    project_is_loaded: bool,
    compare_against_defaults: ApplicableEventConfiguration | None,
):
    if config["enabled"]["effective"]:
        enable_value = "[green]yes[/]"
    else:
        enable_value = "[red]no[/]"
    if config["enabled"]["default"] is None and config["enabled"]["project"] is None:
        if compare_against_defaults is not None:
            enable_value += " (from default)"
        else:
            enable_value += " (not set)"
    elif config["enabled"]["project"] is None and project_is_loaded:
        enable_value += " (from global)"
    tree.add("enabled: " + enable_value)

    if config["wait_time"]["effective"] > 0:
        wait_time_value = f"{config['wait_time']['effective']}s"
    else:
        wait_time_value = "none"
    if config["wait_time"]["default"] is None and config["wait_time"]["project"] is None:
        if compare_against_defaults is not None:
            enable_value += " (from default)"
        else:
            enable_value += " (not set)"
    elif config["wait_time"]["project"] is None and project_is_loaded:
        wait_time_value += " (global)"
    tree.add("wait time: " + wait_time_value)
