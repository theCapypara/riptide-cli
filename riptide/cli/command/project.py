import click
from click import echo, clear
from tqdm import tqdm

from riptide.cli.helpers import cli_section, async_command, RiptideCliError
from riptide.cli.command.base import status as status_cmd
from riptide.cli.lifecycle import start_project, stop_project
from riptide.engine.abstract import ExecError


def load(ctx):
    if "project" in ctx.system_config:
        ctx.command.add_command(start,    'start')
        ctx.command.add_command(start_fg, 'start:fg')
        ctx.command.add_command(stop,     'stop')
        ctx.command.add_command(restart,  'restart')
        ctx.command.add_command(notes,    'notes')
        ctx.command.add_command(cmd,      'cmd')
        if True:  # engine.supports_exec(): TODO TODO
            ctx.command.add_command(exec_cmd, 'exec')


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to start, comma-separated (default: all)')
@async_command
async def start(ctx, services):
    """ TODO DOC """
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
    """ TODO DOC """
    # todo


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to stop, comma-separated (default: all)')
@async_command
async def stop(ctx, services):
    """ TODO DOC """
    if services is not None:
        services = services.split(",")
    await stop_project(ctx, services)


@cli_section("Service")
@click.command()
@click.pass_context
@click.option('--services', '-s', required=False, help='Names of services to restart, comma-separated (default: all)')
@async_command
async def restart(ctx, services):
    """ TODO DOC """
    if services is not None:
        services = services.split(",")
    await stop_project(ctx, services, show_status=False)
    await start_project(ctx, services)


@cli_section("Misc")
@click.command()
def notes():
    """ TODO DOC """
    # todo
    pass


@cli_section("CLI")
@click.command()
def cmd():
    """ TODO DOC """
    # todo
    pass


@cli_section("CLI")
@click.command()
@click.pass_context
@click.argument('service', required=False)
def exec_cmd(ctx, service):
    """ TODO DOC """
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
