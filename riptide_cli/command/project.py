import os
import sys

import click
from click import echo, style, clear
from typing import Union

from riptide.engine.results import ResultQueue
from riptide_cli.helpers import cli_section, async_command, RiptideCliError, TAB
from riptide_cli.lifecycle import start_project, stop_project, display_errors
from riptide_cli.setup_assistant import setup_assistant
from riptide.engine.abstract import ExecError


def load(ctx):
    """Adds project commands to the CLI, if project commands are available"""
    if "project" in ctx.system_config:
        ctx.command.add_command(start,    'start')
        ctx.command.add_command(start_fg, 'start-fg')
        ctx.command.add_command(stop,     'stop')
        ctx.command.add_command(restart,  'restart')
        ctx.command.add_command(cmd,      'cmd')
        ctx.command.add_command(setup,    'setup')
        if ctx.engine.supports_exec():
            ctx.command.add_command(exec_cmd, 'exec')
        if "notices" in ctx.system_config["project"]["app"]:
            ctx.command.add_command(notes,    'notes')


def interrupt_handler(ctx, ex: Union[KeyboardInterrupt, SystemExit]):
    """Handle interrupts raised while running asynchronous AsyncIO code, fun stuff!"""
    # In case there are any open progress bars, close them:
    if hasattr(ctx, "progress_bars"):
        for progress_bar in reversed(ctx.progress_bars.values()):
            progress_bar.close()
            echo()
    if hasattr(ctx, "start_stop_errors"):
        display_errors(ctx.start_stop_errors)
    echo(style('Riptide process was interrupted. '
               'Services might be in an invalid state. You may want to run riptide stop.', bg='red', fg='white'))
    echo("Finishing up... Stand by!")
    # Poison all ResultQueues to halt all start/stop threads after the next step.
    ResultQueue.poison()
    echo("Done!")
    exit(1)


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to start, comma-separated (default: all)')
@async_command(interrupt_handler=interrupt_handler)
async def start(ctx, services):
    """ Starts services. """
    if not ctx.parent.project_is_set_up:
        return please_set_up()
    if services is not None:
        services = services.split(",")
    await start_project(ctx, services)


@cli_section("Service")
@click.command(context_settings={
    'ignore_unknown_options': True  # Make all unknown options redirect to arguments
})
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to start, comma-separated (default: all)')
@click.argument('interactive_service', required=True)
@click.argument('arguments', required=False, nargs=-1, type=click.UNPROCESSED)
@async_command(interrupt_handler=interrupt_handler)
async def start_fg(ctx, services, interactive_service, arguments):
    """
    Starts services and then runs a service in foreground.

    When using this command, Riptide will start all your services
    as normal except for one service you specify.

    This one service will be started in foreground mode. Input and Outputs
    will be attached to the current console.
    You can pass additional arguments to add to the service command.
    This will basically run the service as it were a command.
    This allows for interactive debugging of services.

    If the INTERACTIVE_SERVICE is already started, it is stopped first.

    When running a service in foreground mode the logging options
    for stdout and stderr are ignored.
    stdout and stderr are printed to console instead.

    Following options are also ignored:

    - pre_start

    - post_start

    - roles.src (is set)

    - working_directory (is set to current working directory)

    """

    if not ctx.parent.project_is_set_up:
        return please_set_up()

    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    if "services" not in project["app"] or interactive_service not in project["app"]["services"]:
        raise RiptideCliError("The service %s was not found." % interactive_service, ctx=ctx)

    if services is not None:
        normal_services = services.split(",")
    elif "services" in project["app"]:
        normal_services = list(project["app"]["services"].keys())
    else:
        normal_services = []

    # Remove interactive service from normal service list
    if interactive_service in normal_services:
        normal_services.remove(interactive_service)

    echo(style("(1/3) Starting other services...", bg='cyan', fg='white'))
    await start_project(ctx, normal_services, show_status=False)

    echo(style("(2/3) Stopping %s..." % interactive_service, bg='cyan', fg='white'))
    await stop_project(ctx, [interactive_service], show_status=False)

    echo(style("(3/3) Starting in %s foreground mode..." % interactive_service, bg='cyan', fg='white'))
    engine.service_fg(project, interactive_service, arguments)


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to stop, comma-separated (default: all)')
@async_command(interrupt_handler=interrupt_handler)
async def stop(ctx, services):
    """ Stops services. """
    if not ctx.parent.project_is_set_up:
        return please_set_up()
    if services is not None:
        services = services.split(",")
    await stop_project(ctx, services)


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to restart, comma-separated (default: all)')
@async_command(interrupt_handler=interrupt_handler)
async def restart(ctx, services):
    """ Stops and then starts services. """
    if not ctx.parent.project_is_set_up:
        return please_set_up()
    if services is not None:
        services = services.split(",")
    await stop_project(ctx, services, show_status=False)
    await start_project(ctx, services)


@cli_section("Project")
@click.command()
@click.pass_context
def notes(ctx):
    """ Shows installation and usage notices for this app. """
    notes = ctx.parent.system_config["project"]["app"]["notices"]
    if 'installation' in notes:
        echo(style("Installation notice:", bold=True))
        echo(notes['installation'])

    echo()
    if 'usage' in notes:
        echo(style("General usage notice:", bold=True))
        echo(notes['usage'])


@cli_section("CLI")
@click.command(context_settings={
    'ignore_unknown_options': True  # Make all unknown options redirect to arguments
})
@click.pass_context
@click.argument('command', required=False)
@click.argument('arguments', required=False, nargs=-1, type=click.UNPROCESSED)
def cmd(ctx, command, arguments):
    """
    Executes a project command.
    Project commands are specified in the project configuration.
    The commands are run interactively (Stdout/Stderr/Stdin are attached).
    If you are currently in a subdirectory of 'src' (see project configuration), then the command
    will be executed inside of this directory. Otherwise the command will be executed in the root
    of the 'src' directory. All commands are executed as the current user + group.

    When command is not specified, all commands will be listed.
    """
    if not ctx.parent.project_is_set_up:
        return please_set_up()
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    if command is None:
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

    if "commands" not in project["app"] or command not in project["app"]["commands"]:
        raise RiptideCliError("Command not found.", ctx)

    # check if command is actually an alias
    command = project["app"]["commands"][command].resolve_alias()["$name"]

    # Run Command
    try:
        sys.exit(engine.cmd(project, command, arguments))
    except ExecError as err:
        raise RiptideCliError(str(err), ctx) from err


@cli_section("CLI")
@click.command()
@click.pass_context
@click.option('--root', is_flag=True, default=False, help='Run the shell as the root user instead')
@click.argument('service', required=False)
def exec_cmd(ctx, service, root):
    """
    Opens a shell into a service container.
    The shell is run interactively (Stdout/Stderr/Stdin are attached).
    If you are currently in a subdirectory of 'src' (see project configuration), then the shell
    will be executed inside of this directory. Otherwise the shell will be executed in the root
    of the 'src' directory. Shell is executed as the current user + group (may be named differently inside the container).
    """
    if not ctx.parent.project_is_set_up:
        return please_set_up()
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    if service is None:
        if project["app"].get_service_by_role('main') is None:
            raise RiptideCliError("Please specify a service", ctx)
        service = project["app"].get_service_by_role('main')["$name"]

    try:
        cols, lines = os.get_terminal_size()
        engine.exec(project, service, cols=cols, lines=lines, root=root)
    except ExecError as err:
        raise RiptideCliError(str(err), ctx) from err


@cli_section("Project")
@click.command()
@click.pass_context
@click.option('-f', '--force', is_flag=True, help='Force setup, even if it was already run.')
@click.option('-s', '--skip', is_flag=True, help="Mark project as set up, don't ask any interactive questions")
@async_command()
async def setup(ctx, force, skip):
    """
    Run the initial interactive project setup.
    Guides you through the initial installation of the project
    and through importing already existing project data.
    """
    await setup_assistant(ctx, force, skip)


def please_set_up():
    echo(style("Thanks for using Riptide! You seem to be working with a new project.\n"
               "Please run the ", fg='yellow')
         + style("setup", bold=True, fg='yellow')
         + style(" command first.", fg='yellow'))
