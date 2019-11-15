import os
import shutil

import click
from click import echo
from distutils.dir_util import copy_tree

from riptide_cli.command.constants import CMD_IMPORT_DB, CMD_IMPORT_FILES
from riptide_cli.command.db import importt_impl, cmd_constraint_has_db
from riptide_cli.helpers import cli_section, async_command, RiptideCliError
from riptide_cli.loader import cmd_constraint_project_loaded, load_riptide_core


def cmd_constraint_has_import(ctx):
    cmd_constraint_project_loaded(ctx)
    if "import" not in ctx.system_config["project"]["app"]:
        raise RiptideCliError("The project's app has no import paths defined."
                              "This is required to use this command.", ctx)


def load(main):
    """Adds import commands to the CLI"""

    @cli_section("Import")
    @main.command(CMD_IMPORT_DB)
    @click.argument('file')
    @click.pass_context
    @async_command()
    async def db(ctx, file):
        """ Alias for db:import """
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
        raise RiptideCliError(f"The import key {key} contains an absolute target path. All target paths must be relative to project", ctx)

    destination = os.path.join(project.folder(), import_spec["target"])
    source_is_file = os.path.isfile(path_to_import)

    if os.path.exists(destination) and os.path.isfile(destination):
        raise RiptideCliError(f"The target file ({import_spec['target']}) already exists", ctx)

    if source_is_file and os.path.exists(destination):  # implict: target is directory
        raise RiptideCliError("The target is a diretory, but the path to import points to a file. Can't continue.", ctx)

    echo(f"Importing {key} ({import_spec['target']}) from {path_to_import}")
    echo("Copying... this can take some time...")
    os.makedirs(os.path.dirname(destination ), exist_ok=True)
    try:
        if source_is_file:
            shutil.copy2(path_to_import, destination)
        else:
            copy_tree(path_to_import, destination)
    except Exception as ex:
        raise RiptideCliError("Error while copying", ctx) from ex

    echo("Done!")
