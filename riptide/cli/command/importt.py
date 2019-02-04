import click

from riptide.cli.helpers import cli_section
from riptide.db.environments import DbEnvironments


def load(ctx):
    """Adds import commands to the CLI"""
    if "project" in ctx.system_config and DbEnvironments.has_db(ctx.system_config["project"]):
        ctx.command.add_command(db,  'import:db')
    if "project" in ctx.system_config:  # todo
        ctx.command.add_command(folder,     'import:folder')


@cli_section("Import")
@click.command()
def db():
    """ Alias for db:import """
    return db.importt()


@cli_section("Import")
@click.command()
def folder():
    """ TODO DOC """
    # todo
    pass
