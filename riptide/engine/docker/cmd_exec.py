import os
import pty
import time
from typing import List

from docker.errors import NotFound, APIError

from riptide.config.document.project import Project
from riptide.config.files import CONTAINER_SRC_PATH, get_current_relative_src_path, riptide_assets_dir
from riptide.engine.abstract import ExecError
from riptide.engine.docker.network import get_network_name
from riptide.engine.docker.service import get_container_name, ENTRYPOINT_CONTAINER_PATH, EENV_RUN_MAIN_CMD_AS_USER, \
    EENV_USER, EENV_GROUP, EENV_NO_STDOUT_REDIRECT, parse_entrypoint


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
    # TODO: Get rid of code duplication
    # TODO: Piping | <
    # TODO: Not only /src into container but everything
    if command_name not in project["app"]["commands"]:
        raise ExecError("Command not found.")

    user = os.getuid()
    user_group = os.getgid()

    container_name = get_cmd_container_name(project['name'], command_name)
    command_obj = project["app"]["commands"][command_name]

    # Check if image exists
    try:
        image = client.images.get(command_obj["image"])
    except NotFound:
        print("Riptide: Pulling image... Your command will be run after that.")
        client.api.pull(command_obj['image'] if ":" in command_obj['image'] else command_obj['image'] + ":latest")

    # TODO: The Docker Python API doesn't seem to support interactive run - use pty.spawn for now
    # Containers are run as root, just like the services the entrypoint script manages the rest
    shell = [
        "docker", "run",
        "--rm",
        "-it",
        "-w", CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project),
        "--network", get_network_name(project["name"]),
        "--name", container_name
    ]

    volumes = command_obj.collect_volumes()
    # Add custom entrypoint as volume
    entrypoint_script = os.path.join(riptide_assets_dir(), 'engine', 'docker', 'entrypoint.sh')
    volumes[entrypoint_script] = {'bind': ENTRYPOINT_CONTAINER_PATH, 'mode': 'ro'}

    environment = command_obj.collect_environment()
    # Settings for the entrypoint
    environment[EENV_RUN_MAIN_CMD_AS_USER] = "yes"
    environment[EENV_USER] = str(user)
    environment[EENV_GROUP] = str(user_group)
    environment[EENV_NO_STDOUT_REDIRECT] = "yes"
    # Add original entrypoint, see services.
    image_config = client.api.inspect_image(command_obj["image"])["Config"]
    environment.update(parse_entrypoint(image_config["Entrypoint"]))

    for host, volume in volumes.items():
        shell += ['-v', host + ':' + volume["bind"] + ':' + volume["mode"]]

    for key, value in environment.items():
        shell += ['-e', key + '=' + value]

    shell += [
        "--entrypoint", ENTRYPOINT_CONTAINER_PATH,
        command_obj["image"],
        command_obj["command"] + " " + " ".join('"{0}"'.format(w) for w in arguments)
    ]
    pty.spawn(shell)
