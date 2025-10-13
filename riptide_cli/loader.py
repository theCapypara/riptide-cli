from __future__ import annotations

import os
from typing import TypedDict, cast

from click import Context
from configcrunch import ReferencedDocumentNotFound
from rich.console import Console
from riptide.config.document.config import Config
from riptide.config.files import get_project_setup_flag_path
from riptide.config.hosts import update_hosts_file
from riptide.config.loader import load_config, write_project
from riptide.engine.abstract import AbstractEngine
from riptide.engine.loader import load_engine
from riptide.hook.manager import HookManager
from riptide_cli.command.constants import CMD_CONFIG_EDIT_USER
from riptide_cli.helpers import RiptideCliError, warn
from riptide_cli.hook import RiptideCliHookDisplay
from riptide_cli.shell_integration import update_shell_integration


class RiptideCliCtx(Context):
    console: Console
    loaded: bool
    system_config: Config | None
    project_is_set_up: bool
    engine: AbstractEngine
    hook_manager: HookManager
    riptide_options: RiptideCliOptions


class RiptideCliOptions(TypedDict, total=False):
    project: str | None
    verbose: bool
    skip_hooks: bool
    rename: bool


def load_riptide_system_config(project, skip_project_load=False):
    """
    Loads the system configuration
    :param project:             Project to load, None for auto-detect
    :param skip_project_load:   Skip project loading. If True, the project setting will be ignored
    :return:
    """
    return load_config(project, skip_project_load=skip_project_load)


def load_riptide_core(ctx: RiptideCliCtx, allow_heavy_operations=True, *, skip_project_load=False):
    """
    Loads the project + system config and the configured engine for use with the CLI and the hook manager.

    Also copies the console reference to this context, if the parent context has it.

    If the 'allow_heavy_operations' flag is set, additionally:
    - Updates projects mapping
    - Updates hosts file
    - Loads Shell integration
    - Creates CLI alias scripts
    - Initializes the hook manager (loads git hooks, etc.)
    """
    if ctx.parent is not None:
        ctx.console = ctx.parent.console  # type: ignore

    if not hasattr(ctx, "loaded") or not ctx.loaded:
        # Load the system config (and project).
        ctx.system_config = None
        parent_ctx = cast(RiptideCliCtx, ctx.parent)
        try:
            ctx.system_config = load_riptide_system_config(
                parent_ctx.riptide_options["project"], skip_project_load=skip_project_load
            )
        except FileNotFoundError:
            # Don't show this if the user may have called the command. Since we don't know the invoked command at this
            # point, we just check if the name of the command is anywhere in the protected_args
            if not ctx.resilient_parsing:
                warn(
                    ctx.console,
                    f"You don't have a configuration file for Riptide yet. Use {CMD_CONFIG_EDIT_USER} to create one.",
                    boxed=True,
                )
        except ReferencedDocumentNotFound as ex:
            raise RiptideCliError(
                "Failed to load project because a referenced document could not be found.\n\n"
                "Make sure your repositories are up to date, by running 'riptide update'.",
                ctx,
            ) from ex
        except Exception as ex:
            raise RiptideCliError("Error parsing the system or project configuration.", ctx) from ex
        else:
            if "project" in ctx.system_config:
                if allow_heavy_operations:
                    # Write project name -> path mapping into projects.json file.
                    try:
                        write_project(ctx.system_config["project"], parent_ctx.riptide_options["rename"])
                    except FileExistsError as err:
                        raise RiptideCliError(str(err), ctx) from err
                    # Update /etc/hosts entries for the loaded project
                    update_hosts_file(
                        ctx.system_config, warning_callback=lambda msg: warn(ctx.console, msg, boxed=True)
                    )

                # Check if project setup command was run yet.
                ctx.project_is_set_up = os.path.exists(
                    get_project_setup_flag_path(ctx.system_config["project"].folder())
                )

                if allow_heavy_operations:
                    # Update shell integration
                    update_shell_integration(ctx.system_config)

            # Load engine
            try:
                ctx.engine = load_engine(ctx.system_config["engine"])
                ctx.system_config.load_performance_options(ctx.engine)
            except NotImplementedError as ex:
                raise RiptideCliError("Unknown engine specified in configuration.", ctx) from ex
            except ConnectionError as ex:
                raise RiptideCliError("Connection to engine failed.", ctx) from ex

            # Load the hook manager
            ctx.hook_manager = HookManager(ctx.system_config, ctx.engine, cli=RiptideCliHookDisplay(ctx.console))
            if allow_heavy_operations:
                ctx.hook_manager.setup()

        ctx.loaded = True


def cmd_constraint_project_loaded(ctx: RiptideCliCtx):
    if ctx.system_config is None or "project" not in ctx.system_config:
        raise RiptideCliError("A project must be loaded to use this command.", ctx)
