import os
import stat
import sys

from riptide.config.document.config import Config
from riptide.config.files import get_project_meta_folder
from riptide.config.loader import load_config
from riptide.engine.loader import load_engine


def update_shell_integration(system_config: Config):
    """
    Updates the shell integration by writing a file containing the project name into the _riptide folder
    and writing executables for all commands to the bin-folder.
    """
    # Write project name to file
    meta_folder = get_project_meta_folder(system_config["project"].folder())
    with open(os.path.join(meta_folder, 'name'), 'w') as project_name_file:
        project_name_file.write(system_config["project"]["name"])

    bin_folder = os.path.join(meta_folder, 'bin')
    os.makedirs(bin_folder, exist_ok=True)

    command_files = {f for f in os.listdir(bin_folder) if os.path.isfile(os.path.join(bin_folder, f))}
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
            file.write(f"""#!{sys.executable}
import sys
from riptide_cli.shell_integration import run_cmd
run_cmd("{entry}", sys.argv[1:])
""")

        # Make command alias executable
        st = os.stat(path_to_cmd_file)
        os.chmod(path_to_cmd_file, st.st_mode | stat.S_IEXEC)


def run_cmd(command_name, arguments):
    """Directly run a command in the project found the user is currently in."""
    system_config = load_config()
    engine = load_engine(system_config["engine"])

    # check if command is actually an alias
    command_name = system_config["project"]["app"]["commands"][command_name].resolve_alias()["$name"]
    sys.exit(engine.cmd(system_config["project"], command_name, arguments))
