import os
import re
from appdirs import user_config_dir

RIPTIDE_PROJECT_CONFIG_NAME = 'riptide.yml'
RIPTIDE_PROJECT_META_FOLDER_NAME = '_riptide'

# The path of the source code to be mounted INSIDE the containers
CONTAINER_SRC_PATH = '/src'

def is_path_root(path):
    real_path = os.path.realpath(path)
    parent_real_path = os.path.realpath(os.path.join(real_path, '..'))
    return real_path == parent_real_path


def __discover_project_file__step(path):
    potential_path = os.path.join(path, RIPTIDE_PROJECT_CONFIG_NAME)
    if os.path.exists(potential_path):
        return potential_path
    if is_path_root(path):
        return None
    return __discover_project_file__step(os.path.join(path,'..'))


def discover_project_file():
    return __discover_project_file__step(os.getcwd())


def riptide_assets_dir():
    this_folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(this_folder, '..', '..', 'assets')


def riptide_main_config_file():
    return os.path.join(riptide_config_dir(), 'config.yml')


def riptide_projects_file():
    return os.path.join(riptide_config_dir(), 'projects.json')


def riptide_ports_config_file():
    return os.path.join(riptide_config_dir(), 'ports.json')


def riptide_config_dir():
    return user_config_dir('riptide', False)


def get_project_meta_folder(project_folder_path):
    """
    Get the path to the _riptide folder inside of a project.
    project_folder_path is the folder that the config file of the project is in.
    If the folder does not exist if will be created
    """
    path = os.path.join(project_folder_path, RIPTIDE_PROJECT_META_FOLDER_NAME)
    if not os.path.exists(path):
        os.mkdir(path)
    return path

def remove_all_special_chars(string):
    return re.sub(r"[^a-zA-Z0-9]", "-", string)
