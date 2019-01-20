import os
import stat
import sys

from riptide.config.document.config import Config
from riptide.config.files import get_project_meta_folder
from riptide.config.loader import load_config, load_engine


def load_shell_integration(system_config: Config):
    # Write project name to file
    meta_folder = get_project_meta_folder(system_config["project"].folder())
    with open(os.path.join(meta_folder, 'name'), 'w') as project_name_file:
        project_name_file.write(system_config["project"]["name"])

    bin_folder = os.path.join(meta_folder, 'bin')
    os.makedirs(bin_folder, exist_ok=True)

    command_files = set([f for f in os.listdir(bin_folder) if os.path.isfile(os.path.join(bin_folder, f))])
    if "commands" in system_config["project"]["app"]:
        commands = set(system_config["project"]["app"]["commands"].keys())
    else:
        commands = set()

    # Delete all command alias files for commands that don't exist:
    to_remove = command_files - commands
    for entry in to_remove:
        os.remove(os.path.join(bin_folder, entry))

    # Create command alias files that don't exist yet:
    to_add = commands - command_files
    for entry in to_add:
        path_to_cmd_file = os.path.join(bin_folder, entry)
        with open(path_to_cmd_file, 'w') as file:
            file.write("""#!%s
import sys
from riptide.cli.shell_integration import run_cmd
run_cmd("%s", sys.argv[1:])
""" % (sys.executable, entry))

        st = os.stat(path_to_cmd_file)
        os.chmod(path_to_cmd_file, st.st_mode | stat.S_IEXEC)


def run_cmd(command_name, arguments):
    """Directly run a command in the project found the user is currently in."""
    system_config = load_config()
    engine = load_engine(system_config["engine"])

    # check if command is actually an alias
    # todo: doppelter code
    might_be_alias = True
    while might_be_alias:
        command_obj = system_config["project"]["app"]["commands"][command_name]
        if "aliases" in command_obj:
            command_name = command_obj["aliases"]
        else:
            might_be_alias = False

    engine.cmd(system_config["project"], command_name, arguments)
