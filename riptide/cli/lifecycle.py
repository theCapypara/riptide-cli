from time import sleep

from click import echo, style
from tqdm import tqdm

from riptide.cli.helpers import RiptideCliError, TAB


PROGRESS_TEXT_WIDTH = 35
ERROR_TEXT_WIDTH = 45


def _build_progress_bars(project):
    progress_bars = {}

    longest_service_name_len = len(max(project["app"]["services"].keys(), key=len))

    i = 0
    for service_name in project["app"]["services"]:
        progress_bars[service_name] = tqdm(
            total=1,
            position=i,
            bar_format="{desc}{n_fmt}/{total_fmt}|{bar}| {postfix[0]}",
            postfix=["...".ljust(PROGRESS_TEXT_WIDTH)]
        )
        i += 1
        progress_bars[service_name].set_description(service_name.ljust(longest_service_name_len))
    return progress_bars


def _handle_progress_bar(service_name, status, finished, progress_bars, errors):
    if finished:
        if status:
            # error
            errors.append({"service": service_name, "error": status.cause if status.cause else status})
            msg = (status.message[:ERROR_TEXT_WIDTH-3] + '...') if len(status.message) > ERROR_TEXT_WIDTH-3 else status.message.ljust(ERROR_TEXT_WIDTH)
            progress_bars[service_name].bar_format = "{desc}" + msg
            progress_bars[service_name].refresh()
        else:
            # no error
            pass
    else:
        text_for_status = (status.text[:PROGRESS_TEXT_WIDTH-3] + '...') if len(status.text) > PROGRESS_TEXT_WIDTH-3 else status.text.ljust(PROGRESS_TEXT_WIDTH)
        progress_bars[service_name].postfix[0] = text_for_status
        if progress_bars[service_name].total != status.steps and status.steps is not None:
            progress_bars[service_name].total = status.steps
        # Update increments, so when calling this we need to subtract the current n to get the delta
        progress_bars[service_name].update(status.current_step - progress_bars[service_name].n)
        progress_bars[service_name].refresh()


def _display_errors(errors):
    if len(errors) > 0:
        echo(style("There were errors while starting some of the services: ", fg='red', bold=True))
        for error in errors:
            echo(TAB + style(error["service"] + ":", bold=True, fg='red'))
            echo(TAB + style(str(error["error"]), bg='red'))
            echo()


async def start_project(ctx, show_status=True):
    """ TODO DOC """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    echo("Starting services...")
    echo()

    progress_bars = _build_progress_bars(project)
    errors = []

    try:
        async for service_name, status, finished in engine.start_project(project):
            _handle_progress_bar(service_name, status, finished, progress_bars, errors)
    except Exception as err:
        raise RiptideCliError("Error starting the services", ctx) from err

    for bar in progress_bars.values():
        bar.close()
        echo()

    _display_errors(errors)

    if show_status:
        status_project(ctx)


async def stop_project(ctx, show_status=True):
    """ TODO DOC """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    echo("Stopping services...")
    echo()

    progress_bars = _build_progress_bars(project)
    errors = []

    try:
        async for service_name, status, finished in engine.stop_project(project):
            _handle_progress_bar(service_name, status, finished, progress_bars, errors)
    except Exception as err:
        raise RiptideCliError("Error stopping the services", ctx) from err

    for bar in reversed(list(progress_bars.values())):
        bar.close()
        echo()

    _display_errors(errors)

    if show_status:
        status_project(ctx)


def status_project(ctx):
    """ TODO DOC """
    echo("Status:")
    engine = ctx.parent.engine
    system_config = ctx.parent.system_config
    project = None
    if system_config is None:
        echo(TAB + style('No system configuration found.', fg='yellow'))
    elif "project" in system_config:
        project = system_config["project"]
    if project is None:
        echo(TAB + style('No project found.', fg='yellow'))
    else:
        # todo: in eigene methode + error handling und nice display
        echo(engine.status(project, ctx.parent.system_config))
    pass