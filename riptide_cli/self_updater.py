"""Riptide self-updater."""
import os

from importlib.metadata import packages_distributions
from subprocess import call

from riptide_cli.update_checker import get_version_cache_path


def update():
    print("Updating riptide packages via pip...")
    print()
    packages = [dist for dist in packages_distributions()['riptide'].values()]
    packages.append('configcrunch')
    call("pip3 install --upgrade " + ' '.join(packages), shell=True)
    print()
    try:
        os.remove(get_version_cache_path())
    except Exception:
        pass
    print("Update done! Be sure to also update the repositories and images by running riptide update!")


if __name__ == '__main__':
    update()
