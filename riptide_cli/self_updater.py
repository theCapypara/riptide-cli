"""Riptide self-updater."""

import sys
from subprocess import call


def update():
    print("Updating riptide packages via pip...")
    print()
    from importlib.metadata import distributions

    packages = [dist.name for dist in distributions() if dist.name.startswith("riptide-")]
    packages.append("configcrunch")
    call(f"{sys.executable} -m pip install --upgrade " + " ".join(packages), shell=True)
    print()
    print(
        "Update done! Be sure to restart the proxy server (see documentation) and to update the repositories and images by running riptide update!"
    )


if __name__ == "__main__":
    update()
