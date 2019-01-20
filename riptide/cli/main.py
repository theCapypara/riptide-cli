import os

import click
from click import ClickException, echo, Option, Command, Context
from click_help_colors import HelpColorsGroup

from riptide.cli.command import base as base_commands
from riptide.cli.command import db as db_commands
from riptide.cli.command import importt as import_commands
from riptide.cli.command import project as project_commands
from riptide.cli.command.base import COMMAND_CREATE_CONFIG_USER

from riptide.cli.helpers import RiptideCliError, warn
from riptide.cli.shell_integration import load_shell_integration
from riptide.config.loader import load_config, load_engine
from riptide.config.loader import write_project

"""
todo: 

also: Bash/Zsh support somehow. Am besten via Path. Warnung anzeigen wenn nicht geladen.
also: Bash/Zsh auto-completion - https://click.palletsprojects.com/en/7.x/bashcomplete/

zsh:
if [[ ${chpwd_functions[(I)auto-ls]} -eq 0 ]]; then
  chpwd_functions+=(auto-ls)
fi

bash:
cd, pushd, and popd

"""


def load_cli(ctx, project=None, rename=False, **kwargs):
    ctx.riptide_options = {
        "project": None,
        "verbose": False,
        "fast": False
    }
    ctx.riptide_options.update(kwargs)

    # todo: load git repos if not fast

    ctx.system_config = None
    try:
        ctx.system_config = load_config(project)
    except FileNotFoundError:
        # Don't show this if the user may have called the command. Since we don't know the invoked command at this
        # point, we just check if the name of the command is anywhere in the protected_args
        if COMMAND_CREATE_CONFIG_USER not in ctx.protected_args:
            warn("You don't have a configuration file for Riptide yet. Use %s to create one." % COMMAND_CREATE_CONFIG_USER)
            echo()
    except Exception as ex:
        raise RiptideCliError('Error parsing the system or project configuration.', ctx) from ex
    else:
        if "project" not in ctx.system_config:
            warn("No project found. Are you running riptide inside a riptide project?")
            echo()
        elif not ctx.riptide_options["fast"]:
            # Write project name -> path mapping into projects.json file.
            write_project(ctx.system_config["project"], rename, ctx)
        # Load engine
        try:
            ctx.engine = load_engine(ctx.system_config["engine"])
        except NotImplementedError as ex:
            raise RiptideCliError('Unknown engine specified in configuration.', ctx) from ex
        except ConnectionError as ex:
            raise RiptideCliError('Connection to engine failed.', ctx) from ex

    if 'RIPTIDE_SHELL_LOADED' not in os.environ:
        warn("Riptide shell integration not enabled.")
        echo()

    # Load sub commands
    base_commands.load(ctx)
    if hasattr(ctx, "system_config"):
        project_commands.load(ctx)
        if "project" in ctx.system_config:
            load_shell_integration(ctx.system_config)
        db_commands.load(ctx)
        import_commands.load(ctx)


# TODO: Colored subcommand help
class ClickMainGroup(HelpColorsGroup):
    """
    Special group class that calls the group_callback always as a pre-invoke hook even
    before checking if the subcommand exists.

    Also allows grouping subcommands into sections using the @cli_section annotation.
    """
    def __init__(self, group_callback, *args, **kwargs):
        self.group_callback = group_callback
        self.has_invoked_group_callback = False
        super().__init__(*args, **kwargs)

    def invoke(self, ctx):
        self.invoke_group_callback(ctx)
        return super().invoke(ctx)

    def get_help(self, ctx):
        """
        Run group callback before invoking get_help()
        """
        # TODO: This kinda sucks, because other parameters may not available yet and are ignored.
        self.invoke_group_callback(ctx)
        return super().get_help(ctx)

    def format_commands(self, ctx, formatter):
        """
        Like multi command's version, but also grouping commands into subsections, if avaiable.
        """
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            sections = {}
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                if not hasattr(cmd, 'riptide_section'):
                    cmd.riptide_section = 'General'
                if cmd.riptide_section not in sections:
                    sections[cmd.riptide_section] = []
                sections[cmd.riptide_section].append((subcommand, help))

            for section_name, rows in sections.items():
                with formatter.section(section_name + ' Commands'):
                    # Make sure the spacing between comamnd and help text is always the same, across all sections.
                    spacing = (formatter.width - 6 - max(len(cmd[0]) for cmd in rows)) - limit + 2
                    formatter.write_dl(rows, col_spacing=spacing)

    def invoke_group_callback(self, ctx):
        if not self.has_invoked_group_callback:
            self.has_invoked_group_callback = True
            ctx.invoke(self.group_callback, ctx, **ctx.params)


@click.group(
    cls=ClickMainGroup,
    group_callback=load_cli,
    help_headers_color='yellow',
    help_options_color='cyan'
)
@click.option('-p', '--project', required=False, type=str,
              help="Path to the project file, if not given, the file will be located automatically.")
@click.option('--fast', is_flag=True,
              help="Skip updating repositories and projects list for proxy.")  # TODO explanation
@click.option('-v', '--verbose', is_flag=True,
              help="Print errors and debugging information.")
@click.option('--rename', is_flag=True, hidden=True,
              help="If project with this name already exists at different location, rename it to use this location.")
@click.pass_context
def cli(*args, **kwargs):
    """
    TODO: Description of Riptide here.
    """
    # Nothing needs to be done, everything is in the group_callback
    pass
