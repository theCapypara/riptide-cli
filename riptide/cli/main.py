import click
from click import ClickException
from click_help_colors import HelpColorsGroup


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green'
)
@click.pass_context
def cli(ctx):
    """ Example script. """
    click.echo("CLI")
    ctx.obj = 'Hello World!'


@cli.command('dummy')
@click.pass_obj
def dummy(text):
    """ Dummy """
    click.echo("DUMMY")
    click.echo(text)


@cli.command('dummy:exception')
@click.pass_obj
def dummy_exception(text):
    """ Dummy exception test """
    click.echo(click.style("DUMMY:EXCEPTION", "red"))
    raise ClickException(text)
