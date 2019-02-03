import platform

from docker.types import Mount


def create_mount(target, source, read_only):
    """Create a general-purpose mount object for host-bind volumes used with riptide."""
    return Mount(
        target=target,
        source=source,
        type='bind',
        read_only=read_only,
        consistency='delegated'  # Performance setting for Docker Desktop on Mac
    )


def create_mounts(volumes):
    """Create mount objects from riptide volume lists (:see: Service.collect_volumes)"""
    mounts = []
    for host, volume in volumes.items():
        mounts.append(create_mount(volume['bind'], host, volume['mode'] == 'ro'))
    return mounts


def create_cli_mount_strings(volumes):
    """Retuns a list of parameters for the docker run cli command, representing mounts"""
    volumes_strings = []
    # Mac: Add delegated
    mac_add = ':delegated' if platform.system().lower().startswith('mac') else ''

    for host, volume in volumes.items():
        volumes_strings += ['-v', host + ':' + volume["bind"] + ':' + volume["mode"] + mac_add]
    return volumes_strings
