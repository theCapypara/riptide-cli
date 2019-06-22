import click
import os.path
import yaml
from click import echo, style
from shutil import copyfile

from riptide_cli.helpers import warn, cli_section
from riptide_cli.lifecycle import status_project
from riptide.config.files import riptide_assets_dir, riptide_main_config_file, riptide_config_dir, RIPTIDE_PROJECT_CONFIG_NAME

COMMAND_EDIT_CONFIG_USER = 'config-edit-user'


def load(ctx):
    """Adds all base commands to the CLI"""
    ctx.command.add_command(config_dump,            'config-dump')
    ctx.command.add_command(config_create_user,      COMMAND_EDIT_CONFIG_USER)
    ctx.command.add_command(config_create_project,  'config-edit-project')
    ctx.command.add_command(status,                 'status')


@cli_section("Configuration")
@click.command()
@click.pass_context
@click.option('--system', is_flag=True, default=False,
              help='Also include system-internal keys (keys with $).')
def config_dump(ctx, system=False):
    """
    Outputs the configuration currently in use, as interpreted by Riptide.
    The result is the final configuration that was created by merging all configuration files together
    and resolving all variables.
    """
    echo("# Riptide configuration")
    echo()
    echo("# This is the final configuration that was created by merging all configuration files together")
    echo("# and resolving all variables.")
    final_dict = ctx.parent.system_config.to_dict()
    if not system:
        final_dict = filter_config_dict_recursive_key(final_dict)
    echo(yaml.dump(final_dict, default_flow_style=False, sort_keys=False))


@cli_section("Configuration")
@click.command()
@click.option('--factoryreset', is_flag=True,
              help='Replace your configuration file with the default one (reset it).')
def config_create_user(factoryreset):
    """ Creates or edits the user/system configuration file. """
    config_path = riptide_main_config_file()
    if not os.path.exists(config_path) or factoryreset:
        os.makedirs(riptide_config_dir(), exist_ok=True)
        copyfile(
            os.path.join(riptide_assets_dir(), 'blank_user_config.yml'),
            config_path
        )
        echo('Created config file at ' + style(config_path, bold=True))

    echo('Launching editor to edit the config file...')
    click.edit(filename=config_path)


@cli_section("Configuration")
@click.command()
@click.option('--factoryreset', is_flag=True,
              help='Replace your project file with the default one (reset it).')
def config_create_project(factoryreset):
    """ Creates or edits the project file. """
    config_path = os.path.join(os.getcwd(), RIPTIDE_PROJECT_CONFIG_NAME)
    if not os.path.exists(config_path) or factoryreset:
        os.makedirs(riptide_config_dir(), exist_ok=True)
        copyfile(
            os.path.join(riptide_assets_dir(), 'blank_project_config.yml'),
            config_path
        )
        echo('Created project file at ' + style(config_path, bold=True))

    echo('Launching editor to edit the project file...')
    click.edit(filename=config_path)


@cli_section("Service")
@click.command()
@click.pass_context
def status(ctx):
    """
    Outputs the current status.
    This includes the status of the current project (if any is loaded) and all services of that project.
    """
    status_project(ctx)


def filter_config_dict_recursive_key(final_dict):
    """Filters the dict recursively, removing all $-entries. Not the best performance-solution right now."""
    if not isinstance(final_dict, dict):
        return final_dict
    filtered = {k: v for k, v in final_dict.items() if not k.startswith('$')}
    # Recursion
    return {k: filter_config_dict_recursive_key(v) for k, v in filtered.items()}
