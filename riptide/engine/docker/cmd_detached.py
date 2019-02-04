import os
from typing import List

from docker import DockerClient
from docker.errors import NotFound, ContainerError

from riptide.config.files import riptide_assets_dir
from riptide.engine.docker.mounts import create_mounts
from riptide.engine.docker.network import get_network_name
from riptide.engine.docker.service import ENTRYPOINT_CONTAINER_PATH, parse_entrypoint, EENV_NO_STDOUT_REDIRECT, \
    EENV_RUN_MAIN_CMD_AS_USER, EENV_USER, EENV_GROUP
from riptide.lib.cross_platform.cpuser import getuid, getgid


def cmd_detached(client: DockerClient, project: 'Project', command: 'Command', run_as_root=False) -> (int, str):
    """See AbstractEngine.cmd_detached."""
    user = getuid()
    user_group = getgid()

    name = get_container_name(project["name"])

    # Pulling image
    # Check if image exists
    try:
        client.images.get(command["image"])
    except NotFound:
        image_name_full = command['image'] if ":" in command['image'] else command['image'] + ":latest"
        client.api.pull(image_name_full)

    # Collect volumes
    volumes = command.collect_volumes()
    # Add custom entrypoint as volume
    entrypoint_script = os.path.join(riptide_assets_dir(), 'engine', 'docker', 'entrypoint.sh')
    volumes[entrypoint_script] = {'bind': ENTRYPOINT_CONTAINER_PATH, 'mode': 'ro'}
    mounts = create_mounts(volumes)

    # Collect environment variables
    environment = {}
    # Setup entrypoint. See service start
    image_config = client.api.inspect_image(command["image"])["Config"]
    environment.update(parse_entrypoint(image_config["Entrypoint"]))
    environment[EENV_NO_STDOUT_REDIRECT] = "yes"

    # Change user?
    user_param = None if run_as_root else user
    if user_param:
        environment[EENV_RUN_MAIN_CMD_AS_USER] = "yes"
        environment[EENV_USER] = user
        environment[EENV_GROUP] = user_group

    # Starting the container
    try:
        output = client.containers.run(
            image=command["image"],
            entrypoint=[ENTRYPOINT_CONTAINER_PATH],
            command=command["command"],
            detach=False,
            name=name,
            # user is always root, but EENV_USER may be used to run command with another user using the entrypoint
            group_add=[user_group],
            mounts=mounts,
            environment=environment,
            network=get_network_name(project["name"]),
            remove=True
        )
        return 0, output
    except ContainerError as err:
        return err.exit_status, err.stderr


def get_container_name(project_name: str):
    return 'riptide__' + project_name + '__detached_cmd__' + str(os.getpid())
