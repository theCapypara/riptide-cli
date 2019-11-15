import os
import sys

from click import echo

from configcrunch import ReferencedDocumentNotFound
from riptide.config.files import get_project_setup_flag_path
from riptide.config.hosts import update_hosts_file
from riptide.config.loader import load_config, write_project
from riptide.engine.loader import load_engine
from riptide_cli.command.constants import CMD_CONFIG_EDIT_USER
from riptide_cli.helpers import warn, RiptideCliError
from riptide_cli.shell_integration import update_shell_integration


def load_riptide_system_config(project, skip_project_load=False):
    """
    Loads the system configuration
    :param project:             Project to load, None for auto-detect
    :param skip_project_load:   Skip project loading. If True, the project setting will be ignored
    :return:
    """
    return load_config(project, skip_project_load=skip_project_load)


def load_riptide_core(ctx):
    """
    Loads the project + system config and the configured engine for use with the CLI.
    Also:
    - Loads Shell integration
    - Creates CLI alias scripts
    """
    if not hasattr(ctx, "loaded") or not ctx.loaded:
        # Load the system config (and project).
        ctx.system_config = None
        try:
            ctx.system_config = load_riptide_system_config(ctx.parent.riptide_options['project'])
        except FileNotFoundError:
            # Don't show this if the user may have called the command. Since we don't know the invoked command at this
            # point, we just check if the name of the command is anywhere in the protected_args
            if not ctx.resilient_parsing:
                warn(f"You don't have a configuration file for Riptide yet. Use {CMD_CONFIG_EDIT_USER} to create one.")
                echo()
        except ReferencedDocumentNotFound as ex:
            raise RiptideCliError(
                "Failed to load project because a referenced document could not be found.\n\n"
                "Make sure your repositories are up to date, by running 'riptide update'.", ctx) from ex
        except Exception as ex:
            raise RiptideCliError('Error parsing the system or project configuration.', ctx) from ex
        else:
            if "project" in ctx.system_config:
                # Write project name -> path mapping into projects.json file.
                try:
                    write_project(ctx.system_config["project"], ctx.parent.riptide_options['rename'])
                except FileExistsError as err:
                    raise RiptideCliError(str(err), ctx) from err
                # Update /etc/hosts entries for the loaded project
                update_hosts_file(ctx.system_config, warning_callback=lambda msg: warn(msg))

                # Check if project setup command was run yet.
                ctx.project_is_set_up = os.path.exists(get_project_setup_flag_path(ctx.system_config["project"].folder()))

                # Update shell integration
                update_shell_integration(ctx.system_config)

            # Load engine
            try:
                ctx.engine = load_engine(ctx.system_config["engine"])
            except NotImplementedError as ex:
                raise RiptideCliError('Unknown engine specified in configuration.', ctx) from ex
            except ConnectionError as ex:
                raise RiptideCliError('Connection to engine failed.', ctx) from ex

        ctx.loaded = True


def cmd_constraint_project_loaded(ctx):
    if "project" not in ctx.system_config:
        raise RiptideCliError("A project must be loaded to use this command.", ctx)
