import os
import sys

import click
from click import echo, style
from click.exceptions import Exit
from typing import Union

from riptide.config.command import in_service
from riptide.config.document.command import KEY_IDENTIFIER_IN_SERVICE_COMMAND
from riptide.engine.results import ResultQueue
from riptide_cli.command.constants import CMD_STATUS, CMD_START, CMD_START_FG, CMD_STOP, CMD_RESTART, CMD_CMD, \
    CMD_SETUP, CMD_EXEC, CMD_NOTES
from riptide_cli.helpers import cli_section, async_command, RiptideCliError, TAB, warn
from riptide_cli.lifecycle import start_project, stop_project, display_errors, status_project
from riptide_cli.loader import cmd_constraint_project_loaded, load_riptide_core
from riptide_cli.setup_assistant import setup_assistant
from riptide.engine.abstract import ExecError, AbstractEngine


def interrupt_handler(ctx, ex: Union[KeyboardInterrupt, SystemExit]):
    """Handle interrupts raised while running asynchronous AsyncIO code, fun stuff!"""
    # In case there are any open progress bars, close them:
    if hasattr(ctx, "progress_bars"):
        for progress_bar in reversed(ctx.progress_bars.values()):
            progress_bar.close()
            echo()
    if hasattr(ctx, "start_stop_errors"):
        display_errors(ctx.start_stop_errors, ctx)
    echo(style('Riptide process was interrupted. '
               'Services might be in an invalid state. You may want to run riptide stop.', bg='red', fg='white'))
    echo("Finishing up... Stand by!")
    # Poison all ResultQueues to halt all start/stop threads after the next step.
    ResultQueue.poison()
    echo("Done!")
    exit(1)


def cmd_constraint_project_set_up(ctx):
    cmd_constraint_project_loaded(ctx)
    if not ctx.project_is_set_up:
        echo(style("Thanks for using Riptide! You seem to be working with a new project.\n"
                   "Please run the ", fg='yellow')
             + style("setup", bold=True, fg='yellow')
             + style(" command first.", fg='yellow'))
        raise Exit(1)


def load(main):
    """Adds project commands to the CLI"""

    @cli_section("Service")
    @main.command(CMD_STATUS)
    @click.pass_context
    def status(ctx):
        """
        Outputs the current status.
        This includes the status of the current project (if any is loaded) and all services of that project.
        """
        load_riptide_core(ctx)
        status_project(ctx)

    @cli_section("Service")
    @main.command(CMD_START)
    @click.pass_context
    @click.option('--default', '-d', required=False, is_flag=True, help='Start all default services.')
    @click.option('--all', '-a', required=False, is_flag=True, help='Start all services.')
    @click.option('--services', '-s', required=False, help='Names of services to start, comma-separated (default: all)')
    @async_command(interrupt_handler=interrupt_handler)
    async def start(ctx, default, all, services):
        """
        Starts services.

        By default (or if --default/-d is explicitly set) services defined in `default_services` of the project
        will be started. If none are defined, all services are started.

        If the --all/-a flag is passed, all services are started.

        If --service/-s is passed, a comma-separated list of services is started.

        --default, --service and --all can not be used together.
        """
        load_riptide_core(ctx)
        cmd_constraint_project_set_up(ctx)

        if sum([bool(v) for v in [default, all, services]]) > 1:
            raise RiptideCliError("--all, --service and --default can not be used together", ctx)
        project = ctx.system_config["project"]

        # Default:
        services_to_start = None
        if "default_services" in project:
            services_to_start = project["default_services"]

        if services is not None:
            services_to_start = services.split(",")
        elif all or services_to_start is None:
            services_to_start = project["app"]["services"].keys()

        await start_project(ctx, services_to_start)

    @cli_section("Service")
    @main.command(CMD_START_FG, context_settings={
        'ignore_unknown_options': True  # Make all unknown options redirect to arguments
    })
    @click.pass_context
    @click.option('--default', '-d', required=False, is_flag=True, help='Start all default services.')
    @click.option('--all', '-a', required=False, is_flag=True, help='Start all services.')
    @click.option('--services', '-s', required=False, help='Names of services to start, comma-separated.')
    @click.argument('interactive_service', required=True)
    @click.argument('arguments', required=False, nargs=-1, type=click.UNPROCESSED)
    @async_command(interrupt_handler=interrupt_handler)
    async def start_fg(ctx, default, all, services, interactive_service, arguments):
        """
        Starts services and then runs a service in foreground.

        When using this command, Riptide will start all your services
        as normal except for one service you specify.

        This one service will be started in foreground mode. Input and Outputs
        will be attached to the current console.
        You can pass additional arguments to add to the service command.
        This will basically run the service as it were a command.
        This allows for interactive debugging of services.

        If the INTERACTIVE_SERVICE is already started, it is stopped first.

        When running a service in foreground mode the logging options
        for stdout and stderr are ignored.
        stdout and stderr are printed to console instead.

        Following options are also ignored:

        - pre_start

        - post_start

        - roles.src (is set)

        - working_directory (is set to current working directory)

        For --service/--all/--default flags and default behaviour, see the start command.

        """
        load_riptide_core(ctx)
        cmd_constraint_project_set_up(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine

        if sum([bool(v) for v in [default, all, services]]) > 1:
            raise RiptideCliError("--all, --service and --default can not be used together", ctx)

        if "services" not in project["app"] or interactive_service not in project["app"]["services"]:
            raise RiptideCliError(f"The service {interactive_service} was not found.", ctx=ctx)

        project = ctx.system_config["project"]

        # Default:
        normal_services = None
        if "default_services" in project:
            normal_services = project["default_services"]

        if all or normal_services is None:
            normal_services = list(project["app"]["services"].keys())
        elif services is not None:
            normal_services = services.split(",")

        # Remove interactive service from normal service list
        if interactive_service in normal_services:
            normal_services.remove(interactive_service)

        echo(style("(1/3) Starting other services...", bg='cyan', fg='white'))
        await start_project(ctx, normal_services, show_status=False)

        echo(style(f"(2/3) Stopping {interactive_service}...", bg='cyan', fg='white'))
        await stop_project(ctx, [interactive_service], show_status=False)

        echo(style(f"(3/3) Starting in {interactive_service} foreground mode...", bg='cyan', fg='white'))
        engine.service_fg(project, interactive_service, arguments)

    @cli_section("Service")
    @main.command(CMD_STOP)
    @click.pass_context
    @click.option('--default', '-d', required=False, is_flag=True, help='Stop all default services.')
    @click.option('--all', '-a', required=False, is_flag=True, help='Stop all services.')
    @click.option('--services', '-s', required=False, help='Names of services to stop, comma-separated.')
    @async_command(interrupt_handler=interrupt_handler)
    async def stop(ctx, default, all, services):
        """
        Stops services.

        By default (or if the --all/-a option is explicitly set) all running services are stopped.

        If the --default/-d flag is set, only services defined in the `default_services` of the project are stopped.
        If this field is not set, all services are stopped.

        If --service/-s is passed, a comma-separated list of services is stopped.

        --default, --service and --all can not be used together.
        """
        load_riptide_core(ctx)
        cmd_constraint_project_set_up(ctx)

        if sum([bool(v) for v in [default, all, services]]) > 1:
            raise RiptideCliError("--all, --service and --default can not be used together", ctx)

        project = ctx.system_config["project"]

        # Default: All
        services_to_stop = list(project["app"]["services"].keys())
        if default and "default_services" in project:
            services_to_stop = project["default_services"]
        elif services is not None:
            services_to_stop = services.split(",")

        await stop_project(ctx, services_to_stop)

    @cli_section("Service")
    @main.command(CMD_RESTART)
    @click.pass_context
    @click.option('--default', '-d', required=False, is_flag=True, help='Restart all default services.')
    @click.option('--all', '-a', required=False, is_flag=True, help='Restart all services.')
    @click.option('--services', '-s', required=False, help='Names of services to restart, comma-separated.')
    @async_command(interrupt_handler=interrupt_handler)
    async def restart(ctx, default, all, services):
        """
        Stops and then starts services.

        By default all running services are restarted.

        If the --all/-a flag is set, all services are restarted, even if they were not running.

        If the --default/-d flag is set, only services defined in the `default_services` of the project are restarted,
        including services that were not running. If this field is not set, all services are restarted.

        If --service/-s is passed, a comma-separated list of services is restarted.

        --default, --service and --all can not be used together.

        """
        load_riptide_core(ctx)
        cmd_constraint_project_set_up(ctx)

        if sum([bool(v) for v in [default, all, services]]) > 1:
            raise RiptideCliError("--all, --service and --default can not be used together", ctx)

        project = ctx.system_config["project"]

        # Get running services:
        running_services = [k for (k, v) in ctx.engine.status(project).items() if v]
        # Default (running services):
        services_to_restart = running_services
        if default and "default_services" in project:
            services_to_restart = project["default_services"]
        elif all or (default and "default_services" not in project):
            services_to_restart = project["app"]["services"].keys()
        elif services is not None:
            services_to_restart = services.split(",")

        if len(services_to_restart) < 1:
            raise RiptideCliError("No services were running. "
                                  "If you want to restart all, set the flag -a. See help page.", ctx)

        await stop_project(ctx, services_to_restart, show_status=False)
        await start_project(ctx, services_to_restart)

    @cli_section("Project")
    @main.command(CMD_NOTES)
    @click.pass_context
    def notes(ctx):
        """ Shows installation and usage notices for this app. """
        load_riptide_core(ctx)
        cmd_constraint_project_loaded(ctx)

        if "notices" not in ctx.system_config["project"]["app"]:
            warn("There are no notes defined for this project.")
            return
        notes = ctx.system_config["project"]["app"]["notices"]
        if 'installation' in notes:
            echo(style("Installation notice:", bold=True))
            echo(notes['installation'])

        echo()
        if 'usage' in notes:
            echo(style("General usage notice:", bold=True))
            echo(notes['usage'])

    @cli_section("CLI")
    @main.command(CMD_CMD, context_settings={
        'ignore_unknown_options': True  # Make all unknown options redirect to arguments
    })
    @click.pass_context
    @click.argument('command', required=False)
    @click.argument('arguments', required=False, nargs=-1, type=click.UNPROCESSED)
    def cmd(ctx, command, arguments):
        """
        Executes a project command.
        Project commands are specified in the project configuration.
        The commands are run interactively (Stdout/Stderr/Stdin are attached).
        If you are currently in a subdirectory of 'src' (see project configuration), then the command
        will be executed inside of this directory. Otherwise the command will be executed in the root
        of the 'src' directory. All commands are executed as the current user + group.

        When command is not specified, all commands will be listed.
        """
        load_riptide_core(ctx)
        cmd_constraint_project_set_up(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine

        if command is None:
            click.echo(click.style("Commands:", bold=True))
            if "commands" not in project["app"] or len(project["app"]["commands"]) < 1:
                click.echo(TAB + "No commands specified.")
                return
            for name, cmd in project["app"]["commands"].items():
                if "aliases" in cmd:
                    # alias
                    click.echo(TAB + "- " + click.style(name, bold=True) + " (alias for " + cmd["aliases"] + ")")
                else:
                    # normal / in service cmd
                    click.echo(TAB + "- " + click.style(name, bold=True))
            return

        if "commands" not in project["app"] or command not in project["app"]["commands"]:
            raise RiptideCliError("Command not found.", ctx)

        # check if command is actually an alias
        command = project["app"]["commands"][command].resolve_alias()["$name"]
        cmd_obj = project["app"]["commands"][command]

        # Run Command
        try:
            if KEY_IDENTIFIER_IN_SERVICE_COMMAND in cmd_obj:
                # In Service comamnd
                sys.exit(in_service.run(engine, project, command, arguments))
            else:
                # Normal command
                sys.exit(engine.cmd(project, command, arguments))
        except (ExecError, ValueError) as err:
            raise RiptideCliError(str(err), ctx) from err

    @cli_section("CLI")
    @main.command(CMD_EXEC)
    @click.pass_context
    @click.option('--root', is_flag=True, default=False, help='Run the shell as the root user instead')
    @click.option('--command', default=None, help='Run a custom command instead')
    @click.argument('service', required=False)
    def exec_cmd(ctx, service, root, command):
        """
        Opens a shell into a service container.
        The shell is run interactively (Stdout/Stderr/Stdin are attached).
        If you are currently in a subdirectory of 'src' (see project configuration), then the shell
        will be executed inside of this directory. Otherwise the shell will be executed in the root
        of the 'src' directory. Shell is executed as the current user + group (may be named differently inside the container).

        If --command is given, a command will be executed in the shell. Riptide will not return the exit code of the
        command. Please consider using Command objects instead (riptide cmd). A warning will be printed to stderr first,
        when using this option.
        """
        load_riptide_core(ctx)
        cmd_constraint_project_set_up(ctx)

        project = ctx.system_config["project"]
        engine: AbstractEngine = ctx.engine

        if service is None:
            if project["app"].get_service_by_role('main') is None:
                raise RiptideCliError("Please specify a service", ctx)
            service = project["app"].get_service_by_role('main')["$name"]

        try:
            cols, lines = os.get_terminal_size()
            if not command:
                engine.exec(project, service, cols=cols, lines=lines, root=root)
            else:
                if 'RIPTIDE_DONT_SHOW_EXEC_WARNING' not in os.environ:
                    warn(f"""Using exec --command is not recommended. Please consider creating a Command object instead.

Please see the documentation for more information. 
To suppress this warning, set the environment variable RIPTIDE_DONT_SHOW_EXEC_WARNING.""")

                engine.exec_custom(project, service, command, cols=cols, lines=lines, root=root)
        except ExecError as err:
            raise RiptideCliError(str(err), ctx) from err

    @cli_section("Project")
    @main.command(CMD_SETUP)
    @click.pass_context
    @click.option('-f', '--force', is_flag=True, help='Force setup, even if it was already run.')
    @click.option('-s', '--skip', is_flag=True, help="Mark project as set up, don't ask any interactive questions")
    @async_command()
    async def setup(ctx, force, skip):
        """
        Run the initial interactive project setup.
        Guides you through the initial installation of the project
        and through importing already existing project data.
        """
        load_riptide_core(ctx)
        cmd_constraint_project_loaded(ctx)

        await setup_assistant(ctx, force, skip)
