from typing import Sequence, TypedDict

from rich.console import Group, group
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn
from rich.table import Column, Table
from rich.tree import Tree
from riptide.engine.results import ResultError, StartStopResultStep
from riptide.engine.status import StatusResult, status_for
from riptide.hook.event import HookEvent
from riptide_cli.helpers import RiptideCliError, get_is_verbose
from riptide_cli.hook import trigger_and_handle_hook
from riptide_cli.loader import RiptideCliCtx


def _build_progress_jobs(console_width: int, services: Sequence[str]) -> tuple[Progress, dict[str, TaskID]]:
    """Builds and prepares the progressbar objects for each service"""
    progress = Progress(
        "{task.fields[rip_name]}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.completed}/{task.total}"),
        TextColumn(
            "{task.description}",
            table_column=Column(no_wrap=True, max_width=console_width // 2, min_width=console_width // 2),
        ),
        auto_refresh=False,
    )

    progress_bars = {}
    for service_name in sorted(services):
        progress_bars[service_name] = progress.add_task(rip_name=service_name, description="")
    return progress, progress_bars


class ErrorsDict(TypedDict):
    service: str
    error: ResultError
    error_traceback: str


def _handle_progress_bar(
    service_name: str,
    status: StartStopResultStep | ResultError,
    finished: bool,
    progress: Progress,
    jobs: dict[str, TaskID],
    errors: list[ErrorsDict],
):
    """Handles progress bar updates"""
    if finished:
        if status:
            # error
            traceback_string = "Unknown error."
            if hasattr(status, "traceback_string"):
                traceback_string = status.traceback_string  # type: ignore
            assert isinstance(status, ResultError)
            errors.append({"service": service_name, "error": status, "error_traceback": traceback_string})
            progress.update(jobs[service_name], advance=0, description=f"[white on red]{status.message}")
            task_obj = progress.tasks[jobs[service_name]]
            task_obj.finished_time = task_obj.elapsed
        else:
            # no error
            pass
    else:
        assert isinstance(status, StartStopResultStep)
        progress.update(jobs[service_name], completed=status.current_step, total=status.steps, description=status.text)


def display_errors(errors: list[ErrorsDict], ctx: RiptideCliCtx):
    """Displays errors during start/stop (if any)."""
    if len(errors) > 0:
        verbose = get_is_verbose(ctx)

        errors_table = Table()
        errors_table.add_column("Service")
        errors_table.add_column("Error")
        if verbose:
            errors_table.add_column("Traceback")

            for error in errors:
                errors_table.add_row(
                    escape(error["service"]), escape(str(error["error"])), escape(error["error_traceback"])
                )
        else:
            for error in errors:
                errors_table.add_row(escape(error["service"]), escape(str(error["error"])))

        ctx.console.print(
            Panel(
                Group("There were errors while starting some of the services: ", errors_table),
                title="Errors",
                subtitle="Use -v to show stack traces",
                title_align="left",
                subtitle_align="left",
                border_style="red",
            )
        )


async def start_project(ctx, services: list[str], show_status=True, quick=False, *, command_group: str = "default"):
    """
    Starts a project by starting all it's services (or a subset).
    If show_status is true, shows status after that.
    If quick is True, pre_start and post_start commands are skipped.
    """
    project = ctx.system_config["project"]
    engine = ctx.engine

    if len(services) < 1:
        return

    trigger_and_handle_hook(ctx, HookEvent.PreStart, [",".join(services)])

    progress, jobs = _build_progress_jobs(ctx.console.width, services)
    ctx.start_stop_errors = []

    starting_panel = Panel(progress, title="Starting services...", title_align="left")

    try:
        with Live(starting_panel, refresh_per_second=10, console=ctx.console) as live:
            ctx.live_display = live
            async for service_name, status, finished in engine.start_project(
                project, services, quick=quick, command_group=command_group
            ):
                _handle_progress_bar(service_name, status, finished, progress, jobs, ctx.start_stop_errors)
    except Exception as err:
        raise RiptideCliError("Error starting the services", ctx) from err

    display_errors(ctx.start_stop_errors, ctx)

    status = status_for(project, engine, ctx.system_config)

    trigger_and_handle_hook(
        ctx,
        HookEvent.PostStart,
        [",".join((svc for svc, status_item in status.items() if status_item.running and svc in services))],
    )

    if show_status:
        status_project(ctx, status_items=status)


async def stop_project(ctx, services: list[str], show_status=True):
    """
    Stops a project by stopping all it's services (or a subset).
    If show_status is true, shows status after that.
    """
    project = ctx.system_config["project"]
    engine = ctx.engine

    if len(services) < 1:
        return

    trigger_and_handle_hook(ctx, HookEvent.PreStop, [",".join(services)])

    progress, jobs = _build_progress_jobs(ctx.console.width, services)
    ctx.start_stop_errors = []

    starting_panel = Panel(progress, title="Stopping services...", title_align="left")

    try:
        with Live(starting_panel, refresh_per_second=10, console=ctx.console) as live:
            ctx.live_display = live
            async for service_name, status, finished in engine.stop_project(project, services):
                _handle_progress_bar(service_name, status, finished, progress, jobs, ctx.start_stop_errors)
    except Exception as err:
        raise RiptideCliError("Error stopping the services", ctx) from err

    display_errors(ctx.start_stop_errors, ctx)

    status = status_for(project, engine, ctx.system_config)

    trigger_and_handle_hook(
        ctx,
        HookEvent.PostStop,
        [",".join((svc for svc, status_item in status.items() if not status_item.running))],
    )

    if show_status:
        status_project(ctx, status_items=status)


def status_project(ctx, limit_services=None, *, status_items: dict[str, StatusResult] | None = None):
    """
    Shows the status of Riptide and the loaded project (if any) by collecting data from the engine.
    :type limit_services: None or List that includes names of services to show status for
    :type status_items: Status items to display. If set, these are used,
                        otherwise the status is determined from the configuration and engine.

    """
    ctx.console.print(
        Panel(_status_project_render_group(ctx, limit_services, status_items), title="Status", title_align="left")
    )


@group()
def _status_project_render_group(ctx, limit_services=None, status_items: dict[str, StatusResult] | None = None):
    engine = ctx.engine
    system_config = ctx.system_config
    project = None

    if status_items is None:
        if system_config is None:
            yield "[yellow]No system configuration found."
            return
        elif "project" in system_config:
            project = system_config["project"]
        if project is None:
            yield "[yellow]No project found."
            return
        if not ctx.project_is_set_up:
            yield "[yellow]Project is not yet set up. Run the setup command."
            return
        else:
            status_items = status_for(project, engine, ctx.system_config)

    if status_items is not None:
        if len(status_items) < 1:
            yield "Project loaded, but it contains no services."

        tree = Tree("Services")
        for name, status in status_items.items():
            if limit_services and name not in limit_services:
                continue
            if status.running:
                t_service = tree.add(f"[green]:play_button: {escape(name)}[/]")
            else:
                t_service = tree.add(f"[red]:black_square_for_stop: {escape(name)}[/]")
            if status.running:
                if status.web:
                    t_service.add(f":globe_with_meridians: Web: [underline]{status.web}")
                if len(status.additional_ports) > 0:
                    t_add_ports = t_service.add(":water_wave: Additional Ports:")
                    for port_data in status.additional_ports:
                        t_add_ports.add(
                            f"Port {escape(port_data.title)} ([underline]{port_data.container}[/]) reachable on localhost:[underline]{port_data.host}[/]"
                        )

        yield tree
