import click

from riptide.cli.helpers import cli_section


def load(ctx):
    """Adds import commands to the CLI"""
    if "project" in ctx.system_config:  # todo and role db exists
        ctx.command.add_command(db,  'import:db')
        ctx.command.add_command(db_alias,  'db:import')
    if "project" in ctx.system_config:  # todo
        ctx.command.add_command(folder,     'import:folder')
    if "project" in ctx.system_config:  # todo
        ctx.command.add_command(everything,  'import')


@cli_section("Database")
@click.command()
def db_alias():
    """ Imports a database (alias for import:db). """
    db()


@cli_section("Import")
@click.command()
def db():
    """ TODO DOC """
    # todo
    pass


@cli_section("Import")
@click.command()
def folder():
    """ TODO DOC """
    # todo
    pass


@cli_section("Import")
@click.command()
def everything():
    """ TODO DOC """
    # todo
    pass
