import click
from click import ClickException, echo, Option, Command, Context
from click_help_colors import HelpColorsGroup

from riptide.cli.command import base as base_commands
from riptide.cli.command import command as command_commands
from riptide.cli.command import db as db_commands
from riptide.cli.command import importt as import_commands
from riptide.cli.command import project as project_commands
from riptide.cli.command.base import COMMAND_CREATE_CONFIG_USER

from riptide.cli.helpers import RiptideCliError, warn
from riptide.config.loader import load as load_config

"""
todo:
- Load user config [appdirs]
- Find project
- Load riptide.yml project file
---> config.load module

Global parameters:
-p -- project file direct path. [used by command scripts]
-v -- verbose
--fast -- Don't update repos or check if command files exist [used by command scripts]

Commands (always):
config:dump
config:create:user
config:create:project
status

Commands (with loaded project):
start
stop
restart
notes
command:run (shorthand: cmd)
command:list

Commands (with DB):
db:status
db:list
db:change
db:new
db:copy

Commands (with Import):
import
import:db
import:folder
[import:folder:name]

also: Bash/Zsh support somehow. Am besten via Path. Warnung anzeigen wenn nicht geladen.
also: Bash/Zsh auto-completion - https://click.palletsprojects.com/en/7.x/bashcomplete/

zsh:
if [[ ${chpwd_functions[(I)auto-ls]} -eq 0 ]]; then
  chpwd_functions+=(auto-ls)
fi

bash:
cd, pushd, and popd

"""


def load_cli(ctx, project=None, **kwargs):
    ctx.riptide_options = {
        "project": None,
        "verbose": False,
        "fast": False
    }
    ctx.riptide_options.update(kwargs)

    # todo: load git repos if not fast

    try:
        ctx.system_config = load_config(project)
    except FileNotFoundError:
        # Don't show this if the user may have called the command. Since we don't know the invoked command at this
        # point, we just check if the name of the command is anywhere in fhe protected_args
        if COMMAND_CREATE_CONFIG_USER not in ctx.protected_args:
            warn("You don't have a configuration file for Riptide yet. Use %s to create one." % COMMAND_CREATE_CONFIG_USER)
            echo()
    except Exception as ex:
        raise RiptideCliError('Error parsing the system or project configuration.', ctx) from ex
    else:
        if "project" not in ctx.system_config:
            warn("No project found. Are you running riptide inside a riptide project?")

    # todo: load/update bash integration if not fast
    # todo warnings (no zsh/bash integration ready)

    # Load sub commands
    base_commands.load(ctx)
    """
    TODO
    project_commands.load(ctx)
    db_commands.load(ctx)
    import_commands.load(ctx)
    command_commands.load(ctx)

    """


class ClickMainGroup(HelpColorsGroup):
    def __init__(self, group_callback, *args, **kwargs):
        """
        Special group class that calls the group_callback always as a pre-invoke hook even
        before checking if the subcommand exists.
        """
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
        # TODO: This kinda sucks, because other parameters may not avaiable yet and are therefor ignored.
        self.invoke_group_callback(ctx)
        return super().get_help(ctx)

    def invoke_group_callback(self, ctx):
        if not self.has_invoked_group_callback:
            self.has_invoked_group_callback = True
            ctx.invoke(self.group_callback, ctx, **ctx.params)


@click.group(
    cls=ClickMainGroup,
    group_callback=load_cli,
    help_headers_color='cyan',
    help_options_color='yellow'
)
@click.option('-p', '--project', required=False, type=str,
              help="Path to the project file, if not given, the file will be located automatically.")
@click.option('--fast', is_flag=True,
              help="Skip updating repositories and command files. Disabled by default.")  # TODO explanation
@click.option('-v', '--verbose', is_flag=True,
              help="Print errors and debugging information.")
@click.pass_context
def cli(*args, **kwargs):
    """
    TODO: Description of Riptide here.
    """
    # Nothing needs to be done, everything is in the group_callback
    pass
