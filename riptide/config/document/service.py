import os

from typing import List

from schema import Schema, Optional

from configcrunch import YamlConfigDocument
from riptide.config.files import CONTAINER_SRC_PATH
from riptide.config.service.config_files import *
from riptide.config.service.logging import *


# todo: validate actual schema values -> better schema | ALL documents
class Service(YamlConfigDocument):

    def _initialize_data(self):
        """ Load the absolute path of the config documents specified in config[]["from"]"""
        if self.path:
            folder_of_self = os.path.dirname(self.path)
        else:
            folder_of_self = self.get_project().folder()

        if "config" in self:
            for config in self["config"]:
                # TODO: Currently doesn't allow . or os.sep at the beginning for security reasons.
                if config["from"].startswith(".") or config["from"].startswith(os.sep):
                    raise ValueError("Config 'from' items in services may not start with . or %s." % os.sep)
                config["$source"] = os.path.join(folder_of_self, config["from"])

        if "run_as_root" not in self:
            self.doc["run_as_root"] = False

        if "pre_start" not in self:
            self.doc["pre_start"] = []

        if "post_start" not in self:
            self.doc["post_start"] = []

        if "roles" not in self:
            self.doc["roles"] = []

    @classmethod
    def header(cls) -> str:
        return "service"

    def schema(self) -> Schema:
        return Schema(
            {
                Optional('$ref'): str,  # reference to other Service documents
                Optional('$name'): str,  # Added by system during processing parent app.
                Optional('roles'): [str],
                'image': str,
                Optional('command'): str,
                Optional('port'): int,
                Optional('logging'): {
                    Optional('stdout'): bool,
                    Optional('stderr'): bool,
                    Optional('paths'): {str: str},
                    Optional('commands'): {str: str}
                },
                Optional('pre_start'): [str],
                Optional('post_start'): [str],
                Optional('environment'): [
                    {
                        'name': str,
                        'value': str
                    }
                ],
                Optional('config'): [
                    {
                        'from': str,
                        '$source': str,  # Path to the document that "from" references. Is added durinng loading of service
                        'to': str
                    }
                ],
                # Whether to run as user using riptide or root. Default: False
                Optional('run_as_root'): bool,
                Optional('working_directory'): str,
                Optional('additional_ports'): [
                    {
                        'title': str,
                        'container': int,
                        'host_start': int
                    }
                ],
                Optional('additional_volumes'): [
                    {
                        'host': str,
                        'container': int,
                        Optional('mode'): str  # default: rw - can be rw/ro.
                    }
                ],
                # db only
                Optional('driver'): {
                    'name': str,
                    'access': any  # defined by driver
                }
            }
        )

    def get_project(self):
        try:
            return self.parent_doc.parent_doc
        except Exception as ex:
            raise IndexError("Expected service to have a project assigned") from ex

    def collect_volumes(self):
        """
        Collect volume mappings that this service should be getting when running.
        Volumes are built from following sources:
        - Source code is mounted as volume if role "src" is set
        - Config entries are compiled using Jinja and mounted to their paths
        - Logging files/streams are put into the _riptide/logs folder.
        - If role "db" is set, and a database driver is found, it's volumes are added
        - additional_volumes are added.

        Also creates/updates necessary files and folders
        (eg. compiled configuration, logging).

        Return format is the docker container API volumes dict format.
        See: https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.run
        """
        project = self.get_project()
        volumes = {}

        # role src
        if "src" in self["roles"]:
            volumes[project.src_folder()] = {'bind': CONTAINER_SRC_PATH, 'mode': 'rw'}

        # config
        if "config" in self:
            for config in self["config"]:
                volumes[process_config(config, self)] = {'bind': config["to"], 'mode': 'ro'}

        # logging
        if "logging" in self:
            create_logging_path(self)
            if "stdout" in self["logging"] and self["logging"]["stdout"]:
                volumes[get_logging_path_for(self, 'stdout')] = {'bind': LOGGING_CONTAINER_STDOUT, 'mode': 'rw'}
            if "stderr" in self["logging"] and self["logging"]["stderr"]:
                volumes[get_logging_path_for(self, 'stderr')] = {'bind': LOGGING_CONTAINER_STDERR, 'mode': 'rw'}
            if "paths" in self["logging"]:
                for name, path in self["logging"]["paths"].items():
                    logging_host_path = get_logging_path_for(self, name)
                    volumes[logging_host_path] = {'bind': path, 'mode': 'rw'}
            if "commands" in self["logging"]:
                for name in self["logging"]["commands"].keys():
                    logging_host_path = get_logging_path_for(self, name)
                    logging_command_stdout = get_command_logging_container_path(name)
                    volumes[logging_host_path] = {'bind': logging_command_stdout, 'mode': 'rw'}

        db_driver = self.get_db_driver()
        if db_driver:
            volumes.update(db_driver.collect_volumes())

        # additional_volumes
        if "additional_volumes" in self:
            for vol in self["additional_volumes"]:
                mode = vol["mode"] if "mode" in vol else "rw"
                volumes[vol["host"]] = {'bind': vol["container"], 'mode': mode}

        return volumes

    def collect_environment(self):
        """
        Collect environment variables from the "environment" entry in the service
        configuration.
        Returned format is {key1: value1, key2: value2}
        :return:
        """
        env = {}
        if "environment" in self:
            for env_entry in self["environment"]:
                env[env_entry["name"]] = env_entry["value"]
        return env

    def collect_ports(self):
        """
        Takes additional_ports and returns the actual host/container mappings for these
        ports. The resulting host parts are system-unique, so riptide will not assign
        a port twice across multiple projects/services.
        To achieve this, port bindings are saved into $CONFIG_DIR/ports.json.

        Returned format is {port_service1: port_host1, port_service2: port_host2}
        :return:
        """
        project = self.get_project()
        ports = {}
        if "additional_ports" in self:
            for port_request in self["additional_ports"]:
                ports[port_request["container"]] = get_additional_port(project, self, port_request["host_start"])
        return ports

    def get_db_driver(self):
        """TODO"""
        pass
