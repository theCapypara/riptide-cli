import click
from click import echo

from riptide.cli.helpers import cli_section, async_command, RiptideCliError, TAB
from riptide.cli.lifecycle import start_project, stop_project
from riptide.engine.abstract import ExecError


def load(ctx):
    """Adds project commands to the CLI, if project commands are available"""
    if "project" in ctx.system_config:
        ctx.command.add_command(start,    'start')
        ctx.command.add_command(start_fg, 'start:fg')
        ctx.command.add_command(stop,     'stop')
        ctx.command.add_command(restart,  'restart')
        ctx.command.add_command(cmd,      'cmd')
        if ctx.engine.supports_exec():
            ctx.command.add_command(exec_cmd, 'exec')
        if "installation_notice_text" in ctx.system_config["project"]["app"]:
            ctx.command.add_command(notes,    'notes')


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to start, comma-separated (default: all)')
@async_command
async def start(ctx, services):
    """ Starts services. """
    if services is not None:
        services = services.split(",")
    await start_project(ctx, services)


@cli_section("Service")
@click.command()
@click.pass_context
@click.argument('service', required=False)
@click.option('--services', '-s', required=False, help='Names of additional services to start, comma-separated (default: all)')
@async_command
async def start_fg(ctx, service, services):
    """
    Starts services and runs one in foreground.
    Starts all services specified by --services (or all), except for <service> (main service by default).
    <service> is instead started separately after the rest in foreground mode. Stdin/Stdout/Stderr are attached
    to this service and not written to their log files, even if stdout/stderr logging is enabled for the service.
    """
    # todo


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to stop, comma-separated (default: all)')
@async_command
async def stop(ctx, services):
    """ Stops services. """
    if services is not None:
        services = services.split(",")
    await stop_project(ctx, services)


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to restart, comma-separated (default: all)')
@async_command
async def restart(ctx, services):
    """ Stops and then starts services. """
    if services is not None:
        services = services.split(",")
    await stop_project(ctx, services, show_status=False)
    await start_project(ctx, services)


@cli_section("Misc")
@click.command()
@click.pass_context
def notes(ctx):
    """ Shows the installation notice. """
    echo(ctx.system_config["project"]["app"]["installation_notice_text"])


@cli_section("CLI")
@click.command()
@click.pass_context
@click.argument('command', required=False)
@click.argument('arguments', required=False, nargs=-1)
@click.option('--list', '-l', is_flag=True, help="List all commands")
def cmd(ctx, command, arguments, list):
    """
    Executes a project command.
    Project commands are specified in the project configuration.
    The commands are run interactively (Stdout/Stderr/Stdin are attached).
    If you are currently in a subdirectory of 'src' (see project configuration), then the command
    will be executed inside of this directory. Otherwise the command will be executed in the root
    of the 'src' directory. All commands are executed as the current user + group.
    """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    if list:
        click.echo(click.style("Commands:", bold=True))
        if "commands" not in project["app"] or len(project["app"]["commands"]) < 1:
            click.echo(TAB + "No commands specified.")
            return
        for name, cmd in project["app"]["commands"].items():
            if "aliases" in cmd:
                # alias
                click.echo(TAB + "- " + click.style(name, bold=True) + " (alias for " + cmd["aliases"] + ")")
            else:
                # normal cmd
                click.echo(TAB + "- " + click.style(name, bold=True))
        return

    if command is None:
        raise RiptideCliError("No command specified (--list for list).", ctx)

    if "commands" not in project["app"] or command not in project["app"]["commands"]:
        raise RiptideCliError("Command not found.", ctx)

    # check if command is actually an alias
    command = project["app"]["commands"][command].resolve_alias()["$name"]

    # Run Command
    try:
        engine.cmd(project, command, arguments)
    except ExecError as err:
        raise RiptideCliError(str(err), ctx) from err


@cli_section("CLI")
@click.command()
@click.pass_context
@click.argument('service', required=False)
def exec_cmd(ctx, service):
    """
    Opens a shell into a service container.
    The shell is run interactively (Stdout/Stderr/Stdin are attached).
    If you are currently in a subdirectory of 'src' (see project configuration), then the shell
    will be executed inside of this directory. Otherwise the shell will be executed in the root
    of the 'src' directory. Shell is executed as the current user + group (may be named differently inside the container).
    """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    if service is None:
        if project["app"].get_service_by_role('main') is None:
            raise RiptideCliError("Please specify a service", ctx)
        service = project["app"].get_service_by_role('main')["$name"]

    try:
        engine.exec(project, service)
    except ExecError as err:
        raise RiptideCliError(str(err), ctx) from err
