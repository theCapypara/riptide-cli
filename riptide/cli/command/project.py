import click
from click import echo, clear

from riptide.cli.helpers import cli_section, async_command, RiptideCliError


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
    # todo
    echo("IN START")
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
    try:
        async for service_name, status, finished in engine.start_project(project):
            echo(service_name + " : " + str(status) + " : " + str(finished))
    except Exception as err:
        raise RiptideCliError("Error starting the services", ctx) from err
    echo("DONE")
    echo(engine.status(project))


@cli_section("Service")
@click.command()
@click.pass_context
def start_fg(ctx):
    """ TODO DOC """
    # todo


@cli_section("Service")
@click.command()
def stop():
    """ TODO DOC """
    # todo
    pass


@cli_section("Service")
@click.command()
def restart():
    """ TODO DOC """
    # todo
    pass


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
