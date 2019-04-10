import os
import sys

import pkg_resources
import warnings

import click
from click import echo

from configcrunch import ReferencedDocumentNotFound
from riptide.config.errors import RiptideDeprecationWarning
from riptide.config.hosts import update_hosts_file
from riptide.util import get_riptide_version_raw
from riptide_cli.click import ClickMainGroup
from riptide_cli.command import base as base_commands
from riptide_cli.command import db as db_commands
from riptide_cli.command import importt as import_commands
from riptide_cli.command import project as project_commands
from riptide_cli.command.base import COMMAND_EDIT_CONFIG_USER

from riptide_cli.helpers import RiptideCliError, warn, TAB, header
from riptide_cli.shell_integration import load_shell_integration
from riptide.config.files import get_project_setup_flag_path
from riptide.config.loader import load_config, write_project
from riptide.engine.loader import load_engine
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('always', RiptideDeprecationWarning)


def print_version():
    echo("riptide_lib: %s" % get_riptide_version_raw())
    echo("riptide_cli: %s" % pkg_resources.get_distribution("riptide_cli").version)


def load_cli(ctx, project=None, rename=False, version=False, **kwargs):
    """
    Main function / Group callback to be executed before anything else.
    Loads the global arguments, populates the click context,
    loads the project + system config and the configured engine
    as well as all sub-commands.
    """
    if version:
        print_version()
        exit()

    ctx.riptide_options = {
        "project": None,
        "verbose": False,
        "update": False
    }
    ctx.riptide_options.update(kwargs)

    # TODO: Refactoring

    # Load the system config (and project).
    ctx.system_config = None
    try:
        if ctx.riptide_options['update']:
            echo(header("Updating Riptide repositories..."))
        ctx.system_config = load_config(project,
                                        update_repositories=ctx.riptide_options['update'],
                                        update_func=lambda msg: echo(TAB + msg))
    except FileNotFoundError:
        # Don't show this if the user may have called the command. Since we don't know the invoked command at this
        # point, we just check if the name of the command is anywhere in the protected_args
        if COMMAND_EDIT_CONFIG_USER not in ctx.protected_args and not ctx.resilient_parsing:
            warn("You don't have a configuration file for Riptide yet. Use %s to create one." % COMMAND_EDIT_CONFIG_USER)
            echo()
    except ReferencedDocumentNotFound as ex:
        rerun_note = ""
        # if the update parameter was not provided, tell user to rerun with update parameter
        if not ctx.riptide_options['update']:
            args = sys.argv.copy()
            args.insert(1, '--update')
            rerun_note = "\n\nMake sure your repositories are up to date, by re-running this command with --update:\n" + TAB + TAB + " ".join(args)
        raise RiptideCliError("Failed to load project because a referenced document could not be found." + rerun_note, ctx) from ex
    except Exception as ex:
        raise RiptideCliError('Error parsing the system or project configuration.', ctx) from ex
    else:
        if "project" not in ctx.system_config:
            if not ctx.resilient_parsing:  # Don't show for Auto-complete parsing
                warn("No project found. Are you running Riptide inside a Riptide project?")
                echo()
        else:
            # Write project name -> path mapping into projects.json file.
            try:
                write_project(ctx.system_config["project"], rename)
            except FileExistsError as err:
                raise RiptideCliError(str(err), ctx) from err
            # Update /etc/hosts entries for the loaded project
            update_hosts_file(ctx.system_config, warning_callback=lambda msg: warn(msg))

            # Check if project setup command was run yet.
            ctx.project_is_set_up = os.path.exists(get_project_setup_flag_path(ctx.system_config["project"].folder()))
        # Load engine
        try:
            ctx.engine = load_engine(ctx.system_config["engine"])
        except NotImplementedError as ex:
            raise RiptideCliError('Unknown engine specified in configuration.', ctx) from ex
        except ConnectionError as ex:
            raise RiptideCliError('Connection to engine failed.', ctx) from ex

    # If update is set, also pull images. Repositories are updated above (see load_config())
    if ctx.riptide_options['update'] and ctx.system_config is not None and 'project' in ctx.system_config:
        echo(header("Updating images..."))
        try:
            ctx.engine.pull_images(ctx.system_config["project"],
                                   line_reset="\033[2K\r" + TAB,
                                   update_func=lambda msg: echo(TAB + msg, nl=False))
        except Exception as ex:
            raise RiptideCliError('Error updating an image', ctx) from ex

    if ctx.riptide_options['update']:
        echo(header("End of --update."))

    if 'RIPTIDE_SHELL_LOADED' not in os.environ and not ctx.resilient_parsing:
        # todo: supressable via argument.
        warn("Riptide shell integration not enabled.")
        echo()

    # Load sub commands
    base_commands.load(ctx)
    if ctx.system_config is not None:
        project_commands.load(ctx)
        db_commands.load(ctx)
        import_commands.load(ctx)

        # Set up zsh/bash integration
        if "project" in ctx.system_config:
            load_shell_integration(ctx.system_config)


@click.group(
    cls=ClickMainGroup,
    group_callback=load_cli,
    help_headers_color='yellow',
    help_options_color='cyan'
)
@click.option('-p', '--project', required=False, type=str,
              help="Path to the project file, if not given, the file will be located automatically.")
@click.option('-v', '--verbose', is_flag=True,
              help="Print errors and debugging information.")
@click.option('-u', '--update', is_flag=True,
              help="Update repositories and pull images before executing the command.")
@click.option('--rename', is_flag=True, hidden=True,
              help="If project with this name already exists at different location, rename it to use this location.")
@click.option('--version', is_flag=True,
              help="Print version and exit.")
@click.pass_context
def cli(*args, **kwargs):
    """
    Define development environments for web applications.
    See full documentation at: https://riptide-docs.readthedocs.io/en/latest/
    """
    # Nothing needs to be done, everything is in the group_callback
    pass
