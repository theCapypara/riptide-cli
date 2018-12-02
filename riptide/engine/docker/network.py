from docker import DockerClient
from docker.errors import NotFound


def start(client: DockerClient, project_name: str):
    net_name = get_network_name(project_name)
    try:
        client.networks.get(net_name)
    except NotFound:
        client.networks.create(net_name, driver="bridge", attachable=True)


def get_network_name(project_name: str):
    return 'riptide__' + project_name
