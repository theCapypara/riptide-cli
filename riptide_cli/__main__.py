import asyncio
import os
import warnings
from typing import cast

import click
from click import Context
from rich import traceback
from rich.console import Console
from riptide_cli.loader import RiptideCliCtx
from setproctitle import setproctitle

if __name__ == "__main__":
    warnings.simplefilter("ignore", DeprecationWarning)
    from riptide.config.errors import RiptideDeprecationWarning

    warnings.simplefilter("always", RiptideDeprecationWarning)
    try:
        from cryptography import CryptographyDeprecationWarning  # type: ignore

        warnings.simplefilter("ignore", CryptographyDeprecationWarning)
    except ImportError:
        pass


import riptide_cli.command.config
import riptide_cli.command.db
import riptide_cli.command.hook
import riptide_cli.command.importt
import riptide_cli.command.log
import riptide_cli.command.project
import riptide_cli.command.projects
from riptide.config.loader import load_projects
from riptide.plugin.loader import load_plugins
from riptide.util import SystemFlag
from riptide_cli.click import ClickMainGroup
from riptide_cli.helpers import RiptideCliError, warn


def print_version():
    from importlib.metadata import distributions, version

    dists = distributions()
    for dist in dists:
        if dist.name.startswith("riptide-"):
            print(f"{dist.name:>30}: {version(dist.name)}")


@click.group(name="riptide", cls=ClickMainGroup, help_headers_color="yellow", help_options_color="cyan", chain=True)
@click.option(
    "-P",
    "--project",
    required=False,
    type=str,
    help="Name of the project to use. If not given, will use --project-file.",
)
@click.option(
    "-p",
    "--project-file",
    required=False,
    type=str,
    help="Path to the project file, if not given, the file will be located automatically.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print errors and debugging information.")
@click.option("--skip-hooks", is_flag=True, help="Do not trigger any hooks.")
@click.option(
    "--rename",
    is_flag=True,
    hidden=True,
    help="If project with this name already exists at different location, rename it to use this location.",
)
@click.option("--version", is_flag=True, help="Print version and exit.")
@click.option("-i", "--ignore-shell", is_flag=True, help="Don't print a warning when shell integration is disabled.")
# DEPRECATED OPTIONS:
@click.option(
    "-u",
    "--update",
    is_flag=True,
    hidden=True,
    help="Update repositories and pull images before executing the command.",
)
@click.pass_context
def cli(
    ctx: Context,
    version=False,
    update=False,
    ignore_shell=False,
    project=None,
    project_file=None,
    verbose=False,
    skip_hooks=False,
    **kwargs,
):
    """
    Define development environments for web applications.
    See full documentation at: https://riptide-docs.readthedocs.io/en/latest/
    """
    SystemFlag.IS_CLI = True

    try:
        setproctitle("riptide")
    except Exception:
        pass

    # Print version if requested
    if version:
        print_version()
        exit()

    ctx = cast(RiptideCliCtx, ctx)
    ctx.console = Console()
    traceback.install(show_locals=True, suppress=[click, asyncio])
    ctx.riptide_options = {"verbose": verbose, "skip_hooks": skip_hooks}

    # Don't allow running as root.
    try:
        if os.getuid() == 0 and "RIPTIDE_ALLOW_ROOT" not in os.environ:
            raise RiptideCliError("riptide must not be run as the root user.", ctx=ctx)
    except AttributeError:
        # Windows. Ignore.
        pass

    if project and project_file:
        raise RiptideCliError("--project and --project-file can not be used together.", ctx)

    if update:
        raise RiptideCliError("--update/-u is deprecated. Please run 'riptide update' instead.", ctx)

    if "RIPTIDE_SHELL_LOADED" not in os.environ and not ctx.resilient_parsing and not ignore_shell:
        warn(ctx.console, "Riptide shell integration not enabled.", boxed=True)

    if project:
        projects = load_projects()
        if project in projects:
            project_file = projects[project]
        else:
            raise RiptideCliError(
                f"Project {project} not found. --project/-P "
                f"can only be used if the project was loaded with Riptide at least once.",
                ctx,
            )

    # Setup basic variables
    ctx.riptide_options = {"project": project_file, "verbose": verbose, "skip_hooks": skip_hooks, "rename": False}
    ctx.riptide_options.update(kwargs)  # type: ignore


# Load sub commands
riptide_cli.command.config.load(cli)
riptide_cli.command.db.load(cli)
riptide_cli.command.hook.load(cli)
riptide_cli.command.importt.load(cli)
riptide_cli.command.log.load(cli)
riptide_cli.command.project.load(cli)
riptide_cli.command.projects.load(cli)
for plugin in load_plugins().values():
    plugin.after_load_cli(cli)


if __name__ == "__main__":
    cli()
