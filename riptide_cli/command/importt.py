import os
import shutil
from time import sleep

import click
from rich.live import Live
from rich.panel import Panel
from riptide.hook.additional_volumes import HookHostPathArgument
from riptide.hook.event import HookEvent
from riptide_cli.command.constants import CMD_IMPORT_DB, CMD_IMPORT_FILES
from riptide_cli.command.db import cmd_constraint_has_db, importt_impl
from riptide_cli.helpers import RiptideCliError, async_command, cli_section
from riptide_cli.hook import trigger_and_handle_hook
from riptide_cli.loader import cmd_constraint_project_loaded, load_riptide_core


def cmd_constraint_has_import(ctx):
    cmd_constraint_project_loaded(ctx)
    if "import" not in ctx.system_config["project"]["app"]:
        raise RiptideCliError(
            "The project's app has no import paths defined.This is required to use this command.", ctx
        )


def load(main):
    """Adds import commands to the CLI"""

    @cli_section("Import")
    @main.command(CMD_IMPORT_DB)
    @click.argument("file")
    @click.pass_context
    @async_command()
    async def db(ctx, file):
        """Alias for db:import"""
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        return await importt_impl(ctx, file)

    @cli_section("Import")
    @main.command(CMD_IMPORT_FILES)
    @click.argument("key")
    @click.argument("path_to_import")
    @click.pass_context
    def files(ctx, key, path_to_import):
        """
        Imports file(s).
        To import specify a key to import (import keys; see project configuration)
        and the path to a file or directory to import.
        If the target already exists and isn't a directory, copying will fail
        If the target directory already exists, existing files will not be removed.
        """
        load_riptide_core(ctx)
        cmd_constraint_has_import(ctx)

        files_impl(ctx, key, path_to_import)


def files_impl(ctx, key, path_to_import):
    project = ctx.system_config["project"]

    if key not in project["app"]["import"]:
        raise RiptideCliError("Import key not found. Valid keys are: " + ",".join(project["app"]["import"].keys()), ctx)

    if not os.path.exists(path_to_import):
        raise RiptideCliError("The file or directory to import doesn't exist", ctx)

    import_spec = project["app"]["import"][key]
    if os.path.isabs(import_spec["target"]):
        raise RiptideCliError(
            f"The import key {key} contains an absolute target path. All target paths must be relative to project", ctx
        )

    destination = os.path.join(project.folder(), import_spec["target"])
    source_is_file = os.path.isfile(path_to_import)

    if os.path.exists(destination) and os.path.isfile(destination):
        raise RiptideCliError(f"The target file ({import_spec['target']}) already exists", ctx)

    if source_is_file and os.path.exists(destination):  # implict: target is directory
        raise RiptideCliError("The target is a diretory, but the path to import points to a file. Can't continue.", ctx)

    trigger_and_handle_hook(ctx, HookEvent.PreFileImport, [key, HookHostPathArgument(path_to_import)])

    panel = Panel(
        f"Copying {key} ({import_spec['target']}) from {path_to_import}... this may take a while...",
        title="Importing",
        title_align="left",
    )
    try:
        with Live(panel, refresh_per_second=5, console=ctx.console):
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            if source_is_file:
                shutil.copy2(path_to_import, destination)
            else:
                shutil.copytree(path_to_import, destination, dirs_exist_ok=True)
            sleep(10)
            panel.renderable = "File successfully imported."

    except Exception as ex:
        raise RiptideCliError("Error while copying", ctx) from ex

    trigger_and_handle_hook(ctx, HookEvent.PostFileImport, [key, HookHostPathArgument(path_to_import)])
