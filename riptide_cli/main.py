import os

import pkg_resources
import warnings

import click
from click import echo

from riptide.config.errors import RiptideDeprecationWarning
from riptide.util import get_riptide_version_raw
from riptide_cli.click import ClickMainGroup

from riptide_cli.helpers import RiptideCliError, warn
import riptide_cli.command

warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('always', RiptideDeprecationWarning)


def print_version():
    echo("riptide_lib: %s" % get_riptide_version_raw())
    echo("riptide_cli: %s" % pkg_resources.get_distribution("riptide_cli").version)


@click.group(
    cls=ClickMainGroup,
    help_headers_color='yellow',
    help_options_color='cyan',
    chain=True
)
@click.option('-p', '--project', required=False, type=str,
              help="Path to the project file, if not given, the file will be located automatically.")
@click.option('-v', '--verbose', is_flag=True,
              help="Print errors and debugging information.")
@click.option('--rename', is_flag=True, hidden=True,
              help="If project with this name already exists at different location, rename it to use this location.")
@click.option('--version', is_flag=True,
              help="Print version and exit.")
@click.option('-i', '--ignore-shell', is_flag=True,
              help="Don't print a warning when shell integration is disabled.")
# DEPRECATED OPTIONS:
@click.option('-u', '--update', is_flag=True, hidden=True,
              help="Update repositories and pull images before executing the command.")
@click.pass_context
def cli(ctx, version=False, update=False, ignore_shell=False, **kwargs):
    """
    Define development environments for web applications.
    See full documentation at: https://riptide-docs.readthedocs.io/en/latest/
    """

    # Print version if requested
    if version:
        print_version()
        exit()

    if update:
        raise RiptideCliError("--update/-u is deprecated. Please run 'riptide update' instead.", ctx)

    if 'RIPTIDE_SHELL_LOADED' not in os.environ and not ctx.resilient_parsing and not ignore_shell:
        warn("Riptide shell integration not enabled.")
        echo()

    # Setup basic variables
    ctx.riptide_options = {
        "project": None,
        "verbose": False,
        "rename": False
    }
    ctx.riptide_options.update(kwargs)


# Load sub commands
riptide_cli.command.config.load(cli)
riptide_cli.command.db.load(cli)
riptide_cli.command.importt.load(cli)
riptide_cli.command.project.load(cli)
