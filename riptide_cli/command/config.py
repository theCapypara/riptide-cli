import click
import os.path
import yaml
from click import echo, style
from shutil import copyfile

from riptide.config import repositories
from riptide_cli.command.constants import CMD_CONFIG_DUMP, CMD_CONFIG_EDIT_USER, CMD_CONFIG_EDIT_PROJECT, CMD_UPDATE
from riptide_cli.helpers import cli_section, header, RiptideCliError, TAB
from riptide.config.files import riptide_assets_dir, riptide_main_config_file, riptide_config_dir, RIPTIDE_PROJECT_CONFIG_NAME
from riptide_cli.loader import load_riptide_system_config, load_riptide_core


def load(main):
    """Adds all base commands to the CLI"""

    @cli_section("Configuration")
    @main.command(CMD_CONFIG_DUMP)
    @click.pass_context
    @click.option('--system', is_flag=True, default=False,
                  help='Also include system-internal keys (keys with $).')
    def config_dump(ctx, system=False):
        """
        Outputs the configuration currently in use, as interpreted by Riptide.
        The result is the final configuration that was created by merging all configuration files together
        and resolving all variables.
        """
        load_riptide_core(ctx)
        echo("# Riptide configuration")
        echo()
        echo("# This is the final configuration that was created by merging all configuration files together")
        echo("# and resolving all variables.")
        final_dict = ctx.system_config.to_dict()
        if not system:
            final_dict = _filter_config_dict_recursive_key(final_dict)
        echo(yaml.dump(final_dict, default_flow_style=False, sort_keys=False))

    @cli_section("Configuration")
    @main.command(CMD_CONFIG_EDIT_USER)
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
    @main.command(CMD_CONFIG_EDIT_PROJECT)
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

    @cli_section("Configuration")
    @main.command(CMD_UPDATE)
    @click.pass_context
    def update(ctx):
        """
        Update repositories and current project images
        """
        # Load only the system config
        system_config = load_riptide_system_config(None, skip_project_load=True)

        # Update the repositories
        echo(header("Updating Riptide repositories..."))
        repositories.update(system_config, update_text_func=lambda msg: echo(TAB + msg))

        # Reload system config + project config
        load_riptide_core(ctx)

        # If update is set, also pull images. Repositories are updated above (see load_config())
        if ctx.system_config is not None and 'project' in ctx.system_config:
            echo(header("Updating images..."))
            try:
                ctx.engine.pull_images(ctx.system_config["project"],
                                       line_reset="\033[2K\r" + TAB,
                                       update_func=lambda msg: echo(TAB + msg, nl=False))
            except Exception as ex:
                raise RiptideCliError('Error updating an image', ctx) from ex


def _filter_config_dict_recursive_key(final_dict):
    """Filters the dict recursively, removing all $-entries. Not the best performance-solution right now."""
    if not isinstance(final_dict, dict):
        return final_dict
    filtered = {k: v for k, v in final_dict.items() if not k.startswith('$')}
    # Recursion
    return {k: _filter_config_dict_recursive_key(v) for k, v in filtered.items()}
