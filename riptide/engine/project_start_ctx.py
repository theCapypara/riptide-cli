"""
with-Context object that handles functions that need to be
run before starting or stopping projects
"""
from riptide.config.service.ports import PortsConfig


class StartCtx:
    def __init__(self, project):
        self.project = project

    def __enter__(self):
        # Load the ports.json required for additional_ports
        PortsConfig.load()
        # Let all services run their before_start
        for service in self.project["app"]["services"].values():
            service.before_start()

    def __exit__(self, type, value, traceback):
        # Write the ports.json required for additional_ports
        PortsConfig.write()


def riptide_start_project_ctx(project):
    return StartCtx(project)