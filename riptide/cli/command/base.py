import click
import os.path
from click import echo, style
from shutil import copyfile

from riptide.cli.helpers import warn
from riptide.config.loader import riptide_main_config_file, riptide_config_dir, riptide_assets_dir, \
    RIPTIDE_PROJECT_CONFIG_NAME

COMMAND_CREATE_CONFIG_USER = 'config:create:user'


def load(ctx):
    ctx.command.add_command(config_dump,            'config:dump')
    ctx.command.add_command(config_create_user,     COMMAND_CREATE_CONFIG_USER)
    ctx.command.add_command(config_create_project,  'config:create:project')
    ctx.command.add_command(status,                 'status')


@click.command()
@click.pass_context
def config_dump(ctx):
    """ TODO DOC """
    pass


@click.command()
@click.option('-f', '--force', is_flag=True,
              help='Force creating a new configuration file, even if it already exists.')
@click.option('--edit/--no-edit', default=None,
              help='Specify whether you want to edit the file after creating it '
                   '(or edit the existing file if it already exists). Default is ask.')
def config_create_user(force, edit):
    """ TODO DOC """
    config_path = riptide_main_config_file()
    if os.path.exists(config_path) and not force:
        warn('The config file already exists. It is located at %s. '
             'If you still want to replace it with the default config, pass --force.' % config_path)
    else:
        os.makedirs(riptide_config_dir(), exist_ok=True)
        copyfile(
            os.path.join(riptide_assets_dir(), 'blank_user_config.yml'),
            config_path
        )
        echo('Created config file at ' + style(config_path, bold=True))

    if edit is None:
        edit = click.confirm('Do you want to edit the config file?')
    if edit:
        echo('Launching editor to edit the config file...')
        click.edit(filename=config_path)


@click.command()
@click.option('-f', '--force', is_flag=True,
              help='Force creating a new project file, even if it already exists.')
@click.option('--edit/--no-edit', default=None,
              help='Specify whether you want to edit the file after creating it '
                   '(or edit the existing file if it already exists). Default is ask.')
def config_create_project(force, edit):
    """ TODO DOC """
    config_path = os.path.join(os.getcwd(), RIPTIDE_PROJECT_CONFIG_NAME)
    if os.path.exists(config_path) and not force:
        warn('A project file already exists in the current directory. '
             'If you still want to replace it with the default config, pass --force.')
    else:
        os.makedirs(riptide_config_dir(), exist_ok=True)
        copyfile(
            os.path.join(riptide_assets_dir(), 'blank_project_config.yml'),
            config_path
        )
        echo('Created project file at ' + style(config_path, bold=True))

    if edit is None:
        edit = click.confirm('Do you want to edit the project file?')
    if edit:
        echo('Launching editor to edit the project file...')
        click.edit(filename=config_path)


@click.command()
@click.pass_context
def status(ctx):
    """ TODO DOC """
    pass