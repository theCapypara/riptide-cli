"""Riptide self-updater."""

import pkg_resources
from subprocess import call


def update():
    print("Updating riptide packages via pip...")
    print()
    packages = [dist.project_name for dist in pkg_resources.working_set if dist.project_name.startswith('riptide-')]
    packages.append('configcrunch')
    call("pip3 install --upgrade " + ' '.join(packages), shell=True)
    print()
    print("Update done! Be sure to also update the repositories and images by running riptide update!")


if __name__ == '__main__':
    update()
