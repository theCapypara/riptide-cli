import os
import pty
import time
from typing import List

from docker.errors import NotFound, APIError

from riptide.config.document.project import Project
from riptide.config.files import CONTAINER_SRC_PATH, get_current_relative_src_path
from riptide.engine.abstract import ExecError
from riptide.engine.docker.network import get_network_name
from riptide.engine.docker.service import get_container_name


def service_exec(client, project: Project, service_name: str) -> None:
    if service_name not in project["app"]["services"]:
        raise ExecError("Service not found.")

    container_name = get_container_name(project["name"], service_name)
    service_obj = project["app"]["services"][service_name]

    user = os.getuid()
    user_group = os.getgid()

    try:
        container = client.containers.get(container_name)
        if container.status == "exited":
            container.remove()
            raise ExecError('The service is not running. Try starting it first.')

        # TODO: The Docker Python API doesn't seem to support interactive exec - use pty.spawn for now
        shell = ["docker", "exec", "-it", "-u", str(user) + ":" + str(user_group)]
        if "src" in service_obj["roles"]:
            # Service has source code, set workdir in container to current workdir
            shell += ["-w", CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project)]
        shell += [container_name, "sh", "-c", "if command -v bash >> /dev/null; then bash; else sh; fi"]
        pty.spawn(shell)

    except NotFound:
        raise ExecError('The service is not running. Try starting it first.')
    except APIError as err:
        raise ExecError('Error communicating with the Docker Engine.') from err


def get_cmd_container_name(project_name: str, command_name: str):
    return 'riptide__' + project_name + '__cmd__' + command_name + '__' + str(os.getpid())


def cmd(client, project: Project, command_name: str, arguments: List[str]) -> None:
    if command_name not in project["app"]["commands"]:
        raise ExecError("Command not found.")

    user = os.getuid()
    user_group = os.getgid()

    container_name = get_cmd_container_name(project['name'], command_name)
    command_obj = project["app"]["commands"][command_name]

    # TODO: The Docker Python API doesn't seem to support interactive run - use pty.spawn for now
    shell = [
        "docker", "run",
        "--rm",
        "-it",
        "-u", str(user) + ":" + str(user_group),
        "-w", CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project),
        "--network", get_network_name(project["name"]),
        "--name", container_name
    ]

    volumes = command_obj.collect_volumes()
    environment = command_obj.collect_environment()

    for host, volume in volumes.items():
        shell += ['-v', host + ':' + volume["bind"] + ':' + volume["mode"]]

    for key, value in environment.items():
        shell += ['-e', key + '=' + value]

    shell += [
        command_obj["image"],
        "sh", "-c", command_obj["command"] + " " + " ".join(arguments)
    ]
    pty.spawn(shell)
