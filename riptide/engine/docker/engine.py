import asyncio

import docker
from typing import Tuple, Dict, Union, List

from docker.errors import APIError

from riptide.config.document.config import Config
from riptide.config.document.project import Project
from riptide.engine.abstract import AbstractEngine
from riptide.engine.docker import network, service
from riptide.engine.docker.network import get_network_name
from riptide.engine.docker.service import get_container_name
from riptide.engine.project_start_ctx import riptide_start_project_ctx
from riptide.engine.results import StartStopResultStep, MultiResultQueue, ResultQueue, ResultError
from riptide.engine.docker.cmd_exec import service_exec, cmd


class DockerEngine(AbstractEngine):

    def __init__(self):
        self.client = docker.from_env()
        self.ping()

    def start_project(self, project: Project, services: List[str]) -> MultiResultQueue[StartStopResultStep]:
        with riptide_start_project_ctx(project):
            # Start network
            network.start(self.client, project["name"])

            # Start all services
            queues = {}
            loop = asyncio.get_event_loop()
            for service_name in services:
                # Create queue and add to queues
                queue = ResultQueue()
                queues[queue] = service_name
                if service_name in project["app"]["services"]:
                    # Run start task
                    loop.run_in_executor(
                        None,
                        service.start,

                        project["name"],
                        project["app"]["services"][service_name],
                        self.client,
                        queue
                    )
                else:
                    # Services not found :(
                    queue.end_with_error(queue.end_with_error(ResultError("Service not found.")))

            return MultiResultQueue(queues)

    def stop_project(self, project: Project, services: List[str]) -> MultiResultQueue[StartStopResultStep]:
        # Stop all services
        queues = {}
        loop = asyncio.get_event_loop()

        for service_name in services:
            # Create queue and add to queues
            queue = ResultQueue()
            queues[queue] = service_name
            # Run stop task
            loop.run_in_executor(
                None,
                service.stop,

                project["name"],
                service_name,
                self.client,
                queue
            )

        return MultiResultQueue(queues)

    def status(self, project: Project, system_config: Config) -> Dict[str, bool]:
        services = {}
        for service_name, service_obj in project["app"]["services"].items():
            services[service_name] = service.status(project["name"], service_obj, self.client, system_config)
        return services

    def address_for(self, project: Project, service_name: str) -> Union[None, Tuple[str, int]]:
        container_name = get_container_name(project["name"], service_name)
        network_name = get_network_name(project["name"])
        try:
            ip = self.client.api.inspect_container(container_name)['NetworkSettings']['Networks'][network_name]['IPAddress']
        except KeyError:
            return None
        except APIError:
            return None
        if ip == "" or "port" not in project["app"]["services"][service_name]:
            return None
        port = project["app"]["services"][service_name]["port"]
        return ip, port

    def cmd(self, project: Project, command_name: str) -> None:
        # Start network
        network.start(self.client, project["name"])

        cmd(self.client, project, command_name)

    def exec(self, project: Project, service_name: str) -> None:
        service_exec(self.client, project, service_name)

    def supports_exec(self):
        return True

    def ping(self):
        try:
            self.client.ping()
        except Exception as err:
            raise ConnectionError("Connection with Docker Daemon failed") from err
