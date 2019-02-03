import platform


def optimize_volumes(volumes):
    """Performance optimizations for non-native versions of docker (if available)"""
    if platform.system().lower().startswith('dar'):
        # Mac: Add delegated flag
        # TODO Actually test on mac - May have to use mounts instead:
        #      https://docker-py.readthedocs.io/en/stable/api.html#docker.types.Mount
        for volume in volumes:
            volume['consistency'] = 'delegated'
    return volumes
