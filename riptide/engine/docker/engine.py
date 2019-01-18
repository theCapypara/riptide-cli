import asyncio
import os
import pty
import sys

import docker
from typing import Tuple, Dict, Union, List

import subprocess
from docker.errors import APIError, NotFound

from riptide.config.document.config import Config
from riptide.config.document.project import Project
from riptide.config.files import CONTAINER_SRC_PATH, get_current_relative_project_path, get_current_relative_src_path
from riptide.engine.abstract import AbstractEngine, ExecError
from riptide.engine.docker import network, service
from riptide.engine.docker.network import get_network_name
from riptide.engine.docker.service import get_container_name
from riptide.engine.project_start_ctx import riptide_start_project_ctx
from riptide.engine.results import StatusResult, StartStopResultStep, MultiResultQueue, ResultQueue, ResultError


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

    def status(self, project: Project, system_config: Config) -> Dict[str, StatusResult]:
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
        pass

    def exec(self, project: Project, service_name: str) -> None:
        if service_name not in project["app"]["services"]:
            raise ExecError("Service not found.")

        container_name = get_container_name(project["name"], service_name)
        service_obj = project["app"]["services"][service_name]

        user = os.getuid()

        try:
            container = self.client.containers.get(container_name)
            if container.status == "exited":
                container.remove()
                raise ExecError('The service is not running. Try starting it first.')

            # TODO: The Docker Python API doesn't seem to support interactive exec - use pty.spawn for now
            shell = ["docker", "exec", "-it", "-u", str(user)]
            if "src" in service_obj["roles"]:
                # Service has source code, set workdir in container to current workdir
                shell += ["-w", CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project)]
            shell += [container_name, "sh", "-c", "if command -v bash >> /dev/null; then bash; else sh; fi"]
            pty.spawn(shell)

        except NotFound:
            raise ExecError('The service is not running. Try starting it first.')
        except APIError as err:
            raise ExecError('Error communicating with the Docker Engine.') from err

    def supports_exec(self):
        return True

    def ping(self):
        try:
            self.client.ping()
        except Exception as err:
            raise ConnectionError("Connection with Docker Daemon failed") from err
        pass
