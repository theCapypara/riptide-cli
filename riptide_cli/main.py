import os

import pkg_resources
import warnings

import click
from click import echo

from riptide.config.errors import RiptideDeprecationWarning
from riptide.config.loader import load_projects
from riptide.plugin.loader import load_plugins
from riptide.util import get_riptide_version_raw, SystemFlag
from riptide_cli.click import ClickMainGroup

from riptide_cli.helpers import RiptideCliError, warn
import riptide_cli.command
from riptide_cli.update_checker import check_for_update

warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('always', RiptideDeprecationWarning)


def print_version():
    for pkg in pkg_resources.working_set:
        if pkg.key.startswith('riptide-'):
            print(f"{pkg.key:>30}: {pkg.version}")


@click.group(
    cls=ClickMainGroup,
    help_headers_color='yellow',
    help_options_color='cyan',
    chain=True
)
@click.option('-P', '--project', required=False, type=str,
              help="Name of the project to use. If not given, will use --project-file.")
@click.option('-p', '--project-file', required=False, type=str,
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
def cli(ctx, version=False, update=False, ignore_shell=False, project=None, project_file=None, verbose=False, **kwargs):
    """
    Define development environments for web applications.
    See full documentation at: https://riptide-docs.readthedocs.io/en/latest/
    """
    SystemFlag.IS_CLI = True

    # Print version if requested
    if version:
        print_version()
        exit()

    ctx.riptide_options = {"verbose": verbose}

    # Don't allow running as root.
    try:
        if os.getuid() == 0 and 'RIPTIDE_ALLOW_ROOT' not in os.environ:
            raise RiptideCliError("riptide must not be run as the root user.", ctx=ctx)
    except AttributeError:
        # Windows. Ignore.
        pass

    if project and project_file:
        raise RiptideCliError("--project and --project-file can not be used together.", ctx)

    if update:
        raise RiptideCliError("--update/-u is deprecated. Please run 'riptide update' instead.", ctx)

    new_versions = check_for_update()
    if new_versions:
        new_versions = '\n'.join([f"    {pkg:<22}: {version}" for pkg, version in new_versions.items()])
        warn(f"A new Riptide version is available:\n"
             f"{new_versions}\n\n"
             f"Use riptide_upgrade to upgrade. You may NEED to use sudo, see:\n"
             f"    https://riptide-docs.readthedocs.io/en/latest/user_docs/2a_linux.html#updating-riptide\n", False)

    if 'RIPTIDE_SHELL_LOADED' not in os.environ and not ctx.resilient_parsing and not ignore_shell:
        warn("Riptide shell integration not enabled.")
        echo()

    if project:
        projects = load_projects()
        if project in projects:
            project_file = projects[project]
        else:
            raise RiptideCliError(
                f"Project {project} not found. --project/-P "
                f"can only be used if the project was loaded with Riptide at least once.",
                ctx
            )

    # Setup basic variables
    ctx.riptide_options = {
        "project": project_file,
        "verbose": verbose,
        "rename": False
    }
    ctx.riptide_options.update(kwargs)


# Load sub commands
riptide_cli.command.config.load(cli)
riptide_cli.command.db.load(cli)
riptide_cli.command.importt.load(cli)
riptide_cli.command.project.load(cli)
riptide_cli.command.projects.load(cli)
for plugin in load_plugins().values():
    plugin.after_load_cli(cli)
