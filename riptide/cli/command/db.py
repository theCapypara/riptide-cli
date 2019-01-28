import click

from riptide.cli.helpers import cli_section


def load(ctx):
    """Adds all database commands to the CLI, if database management is available"""
    if "project" in ctx.system_config:  # todo
        ctx.command.add_command(status,  'db:status')
        ctx.command.add_command(lst,     'db:list')
        ctx.command.add_command(change,  'db:change')
        ctx.command.add_command(new,     'db:new')
        ctx.command.add_command(copy,    'db:copy')


@cli_section("Database")
@click.command()
def status():
    """ TODO DOC """
    # todo
    pass


@cli_section("Database")
@click.command()
def lst():
    """ TODO DOC """
    # todo
    pass


@cli_section("Database")
@click.command()
def change():
    """ TODO DOC """
    # todo
    pass


@cli_section("Database")
@click.command()
def new():
    """ TODO DOC """
    # todo
    pass


@cli_section("Database")
@click.command()
def copy():
    """ TODO DOC """
    # todo
    pass
