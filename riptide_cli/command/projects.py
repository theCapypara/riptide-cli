import click

from riptide.config.loader import load_projects, remove_project
from riptide_cli.command.constants import CMD_PROJECT_LIST, CMD_PROJECT_REMOVE
from riptide_cli.helpers import cli_section, TAB, RiptideCliError


def load(main):
    """Adds commands for managing projects (listing, removing, etc.) to the CLI"""

    @cli_section("Project")
    @main.command(CMD_PROJECT_LIST)
    @click.pass_context
    def list(ctx):
        """
        Lists projects.
        This includes all projects that were ever loaded with Riptide.
        """
        click.echo(click.style("Projects:", bold=True))
        projects = load_projects()
        for name, path in projects.items():
            click.echo(TAB + "- " + click.style(name, bold=True) + ": " + path)

    @cli_section("Project")
    @main.command(CMD_PROJECT_REMOVE)
    @click.argument('project', required=True)
    @click.pass_context
    def list(ctx, project):
        """
        Remove a project by name.

        Removing a project will not delete any files. It will only stop it from showing up
        in the proxy server list and it can no longer be used with -P/--project.

        To have the project show up again run riptide status in the directory of the project.

        To permanently remove the data of the Riptide project, remove the riptide.yml file and
        the _riptide directory of the project.
        """
        projects = load_projects()
        if project not in projects:
            raise RiptideCliError(f"Project {project} not found.", ctx)
        remove_project(project)
        click.echo(click.style(f"Project {project} removed."))

