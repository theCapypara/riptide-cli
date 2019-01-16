import click
from click import echo, clear
from tqdm import tqdm

from riptide.cli.helpers import cli_section, async_command, RiptideCliError
from riptide.cli.command.base import status as status_cmd
from riptide.cli.lifecycle import start_project, stop_project


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
@async_command
async def start(ctx):
    """ TODO DOC """
    await start_project(ctx)


@cli_section("Service")
@click.command()
@click.pass_context
def start_fg(ctx):
    """ TODO DOC """
    # todo


@cli_section("Service")
@click.command()
@click.pass_context
@async_command
async def stop(ctx):
    """ TODO DOC """
    await stop_project(ctx)

@cli_section("Service")
@click.command()
@click.pass_context
@async_command
async def restart(ctx):
    """ TODO DOC """
    await stop_project(ctx, show_status=False)
    await start_project(ctx)


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
def exec_cmd():
    """ TODO DOC """
    # todo
    pass
