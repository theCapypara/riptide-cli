from abc import ABC, abstractmethod
from typing import Tuple, Dict, Union

from riptide.config.document.project import Project
from riptide.engine.results import StartResultStep, StopResultStep, StatusResult, MultiResultQueue


class AbstractEngine(ABC):
    @abstractmethod
    def start_project(self, project: Project) -> MultiResultQueue[StartResultStep]:
        """
        Starts all services in the project
        :type project: Project
        :return: MultiResultQueue[StartResult]
        """
        pass

    @abstractmethod
    def stop_project(self, project: Project) -> MultiResultQueue[StopResultStep]:
        """
        Stops all services in the project
        :type project: Project
        :return: MultiResultQueue[StopResult]
        """
        pass

    @abstractmethod
    def status(self, project: Project) -> Dict[str, StatusResult]:
        """
        Returns the status for the given project
        :param project: Project
        :return: StatusResult
        """
        pass

    @abstractmethod
    def address_for(self, project: Project, service_name: str) -> Union[None, Tuple[str, int]]:
        """
        Returns the ip address and port of the host providing the service for project.
        :param project: Project
        :param service_name: str
        :return: Tuple[str, int]
        """
        pass

    @abstractmethod
    def cmd(self, project: Project, command_name: str) -> None:
        """
        Execute the command identified by command_name in the project environment and
        attach command to stdout/stdin/stderr.
        Returns when the command is finished.
        :param project: Project
        :param command_name: str
        :return:
        """

    @abstractmethod
    def exec(self, project: Project, service_name: str) -> None:
        """
        Open an interactive shell into service_name and attach stdout/stdin/stderr.
        Returns when the shell is exited.
        :param project: Project
        :param service_name: str
        :return:
        """
        pass

    @abstractmethod
    def supports_exec(self):
        """
        Whether or not this engine supports exec.
        :return:
        """
        pass
