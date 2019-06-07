"""Riptide self-updater."""
# TODO: Currently pretty stupid script.

import pkg_resources
from subprocess import call


def update():
    print("Updating riptide packages via pip...")
    print()
    packages = [dist.project_name for dist in pkg_resources.working_set if dist.project_name.startswith('riptide-')]
    packages.append('configcrunch')
    call("pip3 install --upgrade " + ' '.join(packages), shell=True)


if __name__ == '__main__':
    update()
