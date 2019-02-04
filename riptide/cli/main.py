import os

import click
from click import echo

from riptide.cli.click import ClickMainGroup
from riptide.cli.command import base as base_commands
from riptide.cli.command import db as db_commands
from riptide.cli.command import importt as import_commands
from riptide.cli.command import project as project_commands
from riptide.cli.command import repo as repo_commands
from riptide.cli.command.base import COMMAND_CREATE_CONFIG_USER

from riptide.cli.helpers import RiptideCliError, warn
from riptide.cli.shell_integration import load_shell_integration
from riptide.config.files import get_project_meta_folder, RIPTIDE_PROJECT_SETUP_FLAG_FILENAME, \
    get_project_setup_flag_path
from riptide.config.loader import load_config, load_engine
from riptide.config.loader import write_project

"""
todo: 
also: Bash/Zsh auto-completion - https://click.palletsprojects.com/en/7.x/bashcomplete/

"""


def load_cli(ctx, project=None, rename=False, **kwargs):
    """
    Main function / Group callback to be executed before anything else.
    Loads the global arguments, populates the click context,
    loads the project + system config and the configured engine
    as well as all sub-commands.
    """
    ctx.riptide_options = {
        "project": None,
        "verbose": False
    }
    ctx.riptide_options.update(kwargs)

    # TODO: Refactoring arguments, and better verbose (use everywhere).
    # todo: load git repos if not fast

    # Load the system config (and project).
    ctx.system_config = None
    try:
        ctx.system_config = load_config(project)
    except FileNotFoundError:
        # Don't show this if the user may have called the command. Since we don't know the invoked command at this
        # point, we just check if the name of the command is anywhere in the protected_args
        if COMMAND_CREATE_CONFIG_USER not in ctx.protected_args and not ctx.resilient_parsing:
            warn("You don't have a configuration file for Riptide yet. Use %s to create one." % COMMAND_CREATE_CONFIG_USER)
            echo()
    except Exception as ex:
        raise RiptideCliError('Error parsing the system or project configuration.', ctx) from ex
    else:
        if "project" not in ctx.system_config and not ctx.resilient_parsing:
            warn("No project found. Are you running Riptide inside a Riptide project?")
            echo()
        else:
            # Write project name -> path mapping into projects.json file.
            write_project(ctx.system_config["project"], rename, ctx)

            # Check if project setup command was run yet.
            ctx.project_is_set_up = os.path.exists(get_project_setup_flag_path(ctx.system_config["project"].folder()))
        # Load engine
        try:
            ctx.engine = load_engine(ctx.system_config["engine"])
        except NotImplementedError as ex:
            raise RiptideCliError('Unknown engine specified in configuration.', ctx) from ex
        except ConnectionError as ex:
            raise RiptideCliError('Connection to engine failed.', ctx) from ex

    if 'RIPTIDE_SHELL_LOADED' not in os.environ and not ctx.resilient_parsing:
        # todo: supressable via argument.
        warn("Riptide shell integration not enabled.")
        echo()

    # Load sub commands
    base_commands.load(ctx)
    if ctx.system_config is not None:
        repo_commands.load(ctx)
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
@click.option('--rename', is_flag=True, hidden=True,
              help="If project with this name already exists at different location, rename it to use this location.")
@click.pass_context
def cli(*args, **kwargs):
    """
    Define development environments for web applications.
    See full documentation at: https://... todo
    """
    # Nothing needs to be done, everything is in the group_callback
    pass
