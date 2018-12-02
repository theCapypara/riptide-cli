import json
import os
from time import sleep

from docker import DockerClient
from docker.errors import NotFound, APIError

from riptide.config.document.config import Config
from riptide.config.document.service import Service
from riptide.engine.docker.network import get_network_name
from riptide.engine.results import ResultQueue, ResultError, StartStopResultStep, StatusResult


def start(project_name: str, service_name: str, service: Service, client: DockerClient, queue: ResultQueue):
    """
    Starts the given service by starting the container (if not already started).

    Finishes when service was successfully started or an error occured.
    Updates the ResultQueue with status messages for this service, as specified by ResultStart.
    If an error during start occurs, an ResultError is added to the queue, indicating the kind of error.
    On errors, tries to execute stop after updating the queue.


    :param client:          Docker Client
    :param project_name:    Name of the project to start
    :param service_name:    Name of the service to start
    :param service:         Service object defining the service
    :param queue:           ResultQueue to update, or None
    """
    # TODO: FG start
    # TODO: WINDOWS?
    user = os.getuid()
    user_group = os.getgid()

    name = get_container_name(project_name, service_name)
    needs_to_be_started = False
    # 1. Check if already running
    queue.put(StartStopResultStep(current_step=1, steps=None, text='Checking...'))
    try:
        container = client.containers.get(name)
        if container.status == "exited":
            container.remove()
            needs_to_be_started = True
    except NotFound:
        needs_to_be_started = True
    except APIError as err:
        queue.end_with_error(ResultError("ERROR checking container status.", cause=err))
        stop(project_name, service_name, client)
        return
    if needs_to_be_started:
        # 2. Pulling image
        try:
            queue.put(StartStopResultStep(current_step=2, steps=4, text="Pulling image... "))
            for line in client.api.pull(service['image'], stream=True):
                status = json.loads(line)
                if "progress" in status:
                    queue.put(StartStopResultStep(current_step=2, steps=4, text="Pulling image... " + status["status"] + " : " + status["progress"]))
                else:
                    queue.put(StartStopResultStep(current_step=2, steps=4, text="Pulling image... " + status["status"]))
        except APIError as err:
            queue.end_with_error(ResultError("ERROR pulling image.", cause=err))
            stop(project_name, service_name, client)
            return

        # 3. Starting the container
        labels = {
            "riptide_project": project_name,
            "riptide_service": service_name,
            "riptide_main": "0"
        }
        if "roles" in service and "main" in service["roles"]:
            labels["riptide_main"] = "1"
        # TODO: post_start and pre_start commands
        # TODO: "Don't wait for start" option
        queue.put(StartStopResultStep(current_step=3, steps=4, text="Starting Container..."))
        try:
            client.containers.run(
                image=service["image"],
                #command=service["command"],
                detach=True,
                name=name,
                network=get_network_name(project_name),
                #user=user,  # todo: how to solve user problem? Maybe: https://denibertovic.com/posts/handling-permissions-with-docker-volumes/
                group_add=[user_group],
                #working_dir=service["working_directory"],
                hostname=service_name,
                labels=labels
            )
        except APIError as err:
            queue.end_with_error(ResultError("ERROR starting container.", cause=err))
            stop(project_name, service_name, client)
            return
        # 4. Checking if it actually started or just crashed immediately
        queue.put(StartStopResultStep(current_step=4, steps=4, text="Checking..."))
        sleep(3)
        try:
            container = client.containers.get(name)
            if container.status == "exited":
                queue.end_with_error(ResultError("ERROR: Container crashed.", details=container.logs().decode("utf-8")))
                container.remove()
                return
        except NotFound:
            queue.end_with_error(ResultError("ERROR: Container went missing."))
            return
        queue.put(StartStopResultStep(current_step=4, steps=4, text="Started!"))
    else:
        queue.put(StartStopResultStep(current_step=2, steps=2, text='Already started!'))
    queue.end()


def stop(project_name: str, service_name: str, client: DockerClient, queue: ResultQueue=None):
    """
    Stops the given service by stopping the container (if not already started).

    Finishes when service was successfully stopped or an error occured.
    Updates the ResultQueue with status messages for this service, as specified by ResultStop.
    If an error during stop occurs, an ResultError is added to the queue, indicating the kind of error.

    The queue is optional.

    :param project_name:    Name of the project to start
    :param service_name:    Name of the service to start
    :param queue:           ResultQueue to update, or None
    """
    name = get_container_name(project_name, service_name)
    # 1. Check if already running
    if queue:
        queue.put(StartStopResultStep(current_step=1, steps=2, text='Checking...'))
    try:
        container = client.containers.get(name)
        # 2. Stop
        if queue:
            queue.put(StartStopResultStep(current_step=2, steps=2, text='Stopping...'))
        container.stop()
        container.remove()
        if queue:
            queue.put(StartStopResultStep(current_step=2, steps=2, text='Stopped!'))
    except NotFound:
        if queue:
            queue.put(StartStopResultStep(current_step=2, steps=2, text='Already stopped!'))
    except APIError as err:
        if queue:
            queue.end_with_error(ResultError("ERROR checking container status.", cause=err))
        return

    if queue:
        queue.end()


def status(project_name: str, service_name: str, service: Service, client: DockerClient, system_config: Config):
    # Get Container
    name = get_container_name(project_name, service_name)
    container_is_running = False
    container = None
    try:
        container = client.containers.get(name)
        if container.status != "exited":
            container_is_running = True
    except NotFound:
        pass

    if container_is_running:
        cstatus = "starting" if container.status == "created" or container.status == "restarting" else "running"
        proxy_url = None
        if "port" in service:
            if "roles" in service and "main" in service["roles"]:
                proxy_url = "http://" + project_name + "." + system_config["proxy"]["url"]
            else:
                proxy_url = "http://" + project_name + "__" + service_name + "." + system_config["proxy"]["url"]
        return StatusResult(
            status=cstatus,
            web=proxy_url,
            additional_ports=None,  ## todo
            logging=None ## todo
        )
    else:
        return StatusResult(
            status="stopped",
            web=None,
            additional_ports=None,
            logging=None
        )


def get_container_name(project_name: str, service_name: str):
    return 'riptide__' + project_name + '__' + service_name
