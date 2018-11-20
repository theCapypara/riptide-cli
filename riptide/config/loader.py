import os

from appdirs import user_config_dir

from riptide.config.document.config import Config
from riptide.config.document.project import Project


RIPTIDE_PROJECT_CONFIG_NAME = 'riptide.yml'


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


def riptide_config_dir():
    return user_config_dir('riptide', False)


def load(project_file=None):
    """
    Loads the specified project file and the system user configuration.
    If no project file is specified, it is auto-detected.

    If the project config could not be found, the project key in the system
    config will not exist. If the system config itself could not be found,
    a FileNotFound error is raised.

    :param project_file: project file to load or none
    :return: config.document.config.Config object.
    :raises: FileNotFoundError if the system config was not found
    :raises: schema.SchemaError on validation errors
    """

    config_path = riptide_main_config_file()

    if project_file:
        project_path = project_file
    else:
        project_path = discover_project_file()

    system_config = Config.from_yaml(config_path)
    system_config.validate()

    if project_path is not None:
        try:
            project_config = Project.from_yaml(project_path)

            # TODO: Translate repos. Da sollen später git repos stehen, nicht direkt pfade.
            project_config.resolve_and_merge_references(system_config["repos"])

            system_config["project"] = project_config
        except FileNotFoundError:
            pass

    system_config.process_vars()

    system_config.validate()

    return system_config
