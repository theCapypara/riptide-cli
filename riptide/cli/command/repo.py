import click

from riptide.cli.helpers import cli_section


def load(ctx):
    """Adds all repository commands to the CLI"""
    ctx.command.add_command(update,  'update')


@cli_section("Repository")
@click.command()
@click.pass_context
def update(ctx):
    """
    Updates repositories for app, services, etc.
    Updates the code of all configured repository that are searched for $ref-references.
    """
    # todo
    pass