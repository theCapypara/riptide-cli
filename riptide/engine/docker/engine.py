import asyncio
import docker
from typing import Tuple, Dict, Union

from docker.errors import APIError

from riptide.config.document.config import Config
from riptide.config.document.project import Project
from riptide.engine.abstract import AbstractEngine
from riptide.engine.docker import network, service
from riptide.engine.docker.network import get_network_name
from riptide.engine.docker.service import get_container_name
from riptide.engine.results import StatusResult, StartStopResultStep, MultiResultQueue, ResultQueue


class DockerEngine(AbstractEngine):

    def __init__(self):
        self.client = docker.from_env()

    def start_project(self, project: Project) -> MultiResultQueue[StartStopResultStep]:
        self.ping()
        # Start network
        network.start(self.client, project["name"])

        # Start all services
        queues = {}
        loop = asyncio.get_event_loop()
        for service_name, service_obj in project["app"]["services"].items():
            # Create queue and add to queues
            queue = ResultQueue()
            queues[queue] = service_name
            # Run start task
            loop.run_in_executor(
                None,
                service.start,

                project["name"],
                service_name,
                service_obj,
                self.client,
                queue
            )

        return MultiResultQueue(queues)

    def stop_project(self, project: Project) -> MultiResultQueue[StartStopResultStep]:
        self.ping()
        # Stop all services
        queues = {}
        loop = asyncio.get_event_loop()
        for service_name in project["app"]["services"].keys():
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

    def status(self, project: Project, system_config: Config) -> Dict[str, StatusResult]:
        self.ping()
        services = {}
        for service_name, service_obj in project["app"]["services"].items():
            services[service_name] = service.status(project["name"], service_name, service_obj, self.client, system_config)
        return services

    def address_for(self, project: Project, service_name: str) -> Union[None, Tuple[str, int]]:
        self.ping()
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
        self.ping()
        pass

    def exec(self, project: Project, service_name: str) -> None:
        self.ping()
        pass

    def supports_exec(self):
        return True

    def ping(self):
        try:
            self.client.ping()
        except Exception as err:
            raise ConnectionError("Connection with Docker Daemon failed") from err
        pass
