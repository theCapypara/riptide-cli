import os
from collections import OrderedDict
from typing import List

from click import echo, style
from tqdm import tqdm

from riptide.engine.status import status_for
from riptide_cli.helpers import RiptideCliError, TAB, get_is_verbose


def text_width_right():
    """returns ~40% of terminal width space in characters"""
    try:
        return round(os.get_terminal_size()[0] * 0.4)
    except OSError:
        return 45  # Fallback


def text_width_error():
    """returns ~70% of terminal width space in characters"""
    try:
        return round(os.get_terminal_size()[0] * 0.7)
    except OSError:
        return 45  # Fallback


def _build_progress_bars(services):
    """Builds and prepares the progressbar objects for each service"""
    progress_bars = OrderedDict()

    longest_service_name_len = len(max(services, key=len))

    i = 0
    for service_name in services:
        progress_bars[service_name] = tqdm(
            total=1,
            position=i,
            bar_format="{desc}{n_fmt}/{total_fmt}|{bar}| {postfix[0]}",
            postfix=["...".ljust(text_width_right())]
        )
        i += 1
        progress_bars[service_name].set_description(service_name.ljust(longest_service_name_len))
    return progress_bars


def _handle_progress_bar(service_name, status, finished, progress_bars, errors):
    """Handles progress bar updates"""
    if finished:
        if status:
            # error
            tw = text_width_error()
            traceback_string = 'Unknown error.'
            if hasattr(status, 'traceback_string'):
                traceback_string = status.traceback_string
            errors.append({
                "service": service_name,
                "error": status,
                "error_traceback": traceback_string
            })
            msg = (status.message[:tw-3] + '...') if len(status.message) > tw-3 else status.message.ljust(tw)
            progress_bars[service_name].bar_format = "{desc}" + msg
            progress_bars[service_name].refresh()
        else:
            # no error
            pass
    else:
        tw = text_width_right()
        text_for_status = (status.text[:tw-3] + '...') if len(status.text) > tw-3 else status.text.ljust(tw)
        progress_bars[service_name].postfix[0] = text_for_status
        if progress_bars[service_name].total != status.steps and status.steps is not None:
            progress_bars[service_name].total = status.steps
        # Update increments, so when calling this we need to subtract the current n to get the delta
        progress_bars[service_name].update(status.current_step - progress_bars[service_name].n)
        progress_bars[service_name].refresh()


def display_errors(errors, ctx):
    """Displays errors during start/stop (if any)."""
    if len(errors) > 0:
        echo(style("There were errors while starting some of the services (use -v to show tracebacks): ", fg='red', bold=True))
        for error in errors:
            echo(TAB + style(error["service"] + ":", bold=True, fg='red'))
            echo(TAB + style(str(error["error"]), bg='red'))
            if get_is_verbose(ctx):
                echo(style(str(error["error_traceback"]), bg='red'))


async def start_project(ctx, services: List[str], show_status=True, quick=False):
    """
    Starts a project by starting all it's services (or a subset).
    If show_status is true, shows status after that.
    If quick is True, pre_start and post_start commands are skipped.
    """
    project = ctx.system_config["project"]
    engine = ctx.engine

    if len(services) < 1:
        return

    echo("Starting services...")
    echo()

    ctx.progress_bars = _build_progress_bars(services)
    ctx.start_stop_errors = []

    try:
        async for service_name, status, finished in engine.start_project(project, services, quick=quick):
            _handle_progress_bar(service_name, status, finished, ctx.progress_bars, ctx.start_stop_errors)
    except Exception as err:
        raise RiptideCliError("Error starting the services", ctx) from err

    for bar in reversed(ctx.progress_bars.values()):
        bar.close()
        echo()

    display_errors(ctx.start_stop_errors, ctx)

    if show_status:
        status_project(ctx)


async def stop_project(ctx, services: List[str], show_status=True):
    """
    Stops a project by stopping all it's services (or a subset).
    If show_status is true, shows status after that.
    """
    project = ctx.system_config["project"]
    engine = ctx.engine

    if len(services) < 1:
        return

    echo("Stopping services...")
    echo()

    ctx.progress_bars = _build_progress_bars(services)
    ctx.start_stop_errors = []

    try:
        async for service_name, status, finished in engine.stop_project(project, services):
            _handle_progress_bar(service_name, status, finished, ctx.progress_bars, ctx.start_stop_errors)
    except Exception as err:
        raise RiptideCliError("Error stopping the services", ctx) from err

    for bar in reversed(ctx.progress_bars.values()):
        bar.close()
        echo()

    display_errors(ctx.start_stop_errors, ctx)

    if show_status:
        status_project(ctx)


def status_project(ctx, limit_services=None):
    """
    Shows the status of Riptide and the loaded project (if any) by collecting data from the engine.
    :type limit_services: None or List that includes names of services to show status for

    """
    echo("Status:")
    engine = ctx.engine
    system_config = ctx.system_config
    project = None
    if system_config is None:
        echo(TAB + style('No system configuration found.', fg='yellow'))
    elif "project" in system_config:
        project = system_config["project"]
    if project is None:
        echo(TAB + style('No project found.', fg='yellow'))
        return
    if not ctx.project_is_set_up:
        echo(TAB + style('Project is not yet set up. Run the setup command.', fg='yellow'))
        return
    else:
        status_items = status_for(project, engine, ctx.system_config).items()
        if len(status_items) < 1:
            echo(TAB + "Project loaded, but it contains no services.")

        for name, status in status_items:
            if limit_services and name not in limit_services:
                continue
            echo(TAB + style(name + ':', fg='green' if status.running else 'red', bold=True))
            if not status.running:
                echo(TAB + TAB + 'Not running.')
            else:
                echo(TAB + TAB + 'Running.')
                if status.web:
                    echo(TAB + TAB + 'Access via ' + style(status.web, bold=True))
                if len(status.additional_ports) > 0:
                    echo(TAB + TAB + 'Additional Ports:')
                    for port_data in status.additional_ports:
                        echo(TAB + TAB + TAB + 'Port %s (%d) reachable on localhost:%s' %
                             (style(port_data.title, bold=True), port_data.container, style(str(port_data.host), bold=True))
                         )

            echo()
