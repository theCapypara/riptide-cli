import json
import os
from asyncio import sleep

import click
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from riptide.db.driver import db_driver_for_service
from riptide.db.environments import DbEnvironments
from riptide.hook.additional_volumes import HookHostPathArgument
from riptide.hook.event import HookEvent
from riptide_cli.command.constants import (
    CMD_DB_COPY,
    CMD_DB_DROP,
    CMD_DB_EXPORT,
    CMD_DB_IMPORT,
    CMD_DB_LIST,
    CMD_DB_NEW,
    CMD_DB_STATUS,
    CMD_DB_SWITCH,
)
from riptide_cli.helpers import RiptideCliError, async_command, cli_section
from riptide_cli.hook import trigger_and_handle_hook
from riptide_cli.lifecycle import start_project, stop_project
from riptide_cli.loader import cmd_constraint_project_loaded, load_riptide_core


def cmd_constraint_has_db(ctx):
    cmd_constraint_project_loaded(ctx)
    if not DbEnvironments.has_db(ctx.system_config["project"]):
        raise RiptideCliError(
            "The project doesn't have a service with the role 'db'. This is required to use this command.", ctx
        )


def load(main):
    """Adds all database commands to the CLI"""

    @cli_section("Database")
    @main.command(CMD_DB_STATUS)
    @click.pass_context
    def status(ctx):
        """
        Print information and status of the database.
        """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)
        assert dbenv.db_service is not None
        db_driver = db_driver_for_service.get(dbenv.db_service)
        assert db_driver is not None  # todo: error handling

        running = engine.service_status(project, dbenv.db_service["$name"])
        current = dbenv.currently_selected_name()

        grid = Table.grid(expand=False)
        grid.add_column()
        grid.add_column()
        grid.add_row("Active environment: ", current)
        grid.add_row("Service: ", dbenv.db_service["$name"])
        if running:
            running_text = "[green]:play_button: Running"
        else:
            running_text = "[red]:black_square_for_stop: Not running"
        grid.add_row("Status: ", running_text)
        for key, label in db_driver.collect_info().items():
            grid.add_row(escape(key) + ": ", escape(label))

        ctx.console.print(grid)

    @cli_section("Database")
    @main.command(CMD_DB_LIST)
    @click.pass_context
    @click.option("--machine-readable", is_flag=True, default=False, help="Print machine readable output (JSON)")
    @click.option("--current", is_flag=True, default=False, help="Print current used env")
    def lst(ctx, machine_readable, current):
        """Lists database environments"""
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        cur = dbenv.currently_selected_name()

        if not machine_readable and not current:
            db_tree = Tree("Database environments")

            for env in dbenv.list():
                if env == cur:
                    db_tree.add(f"{env} [bold](Current)[/]")
                else:
                    db_tree.add(env)

            ctx.console.print(db_tree)
        elif not current:
            print(json.dumps({"envs": dbenv.list(), "current": cur}))
        else:
            print(cur)

    @cli_section("Database")
    @main.command(CMD_DB_SWITCH)
    @click.pass_context
    @click.argument("name")
    @async_command()
    async def switch(ctx, name):
        """Switches the active database environment"""
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        await switch_impl(ctx, name)

    @cli_section("Database")
    @main.command(CMD_DB_NEW)
    @click.pass_context
    @click.option("-s", "--stay", is_flag=True, help="If set, don't switch to the newly created environment.")
    @click.argument("name")
    @async_command()
    async def new(ctx, stay, name):
        """Create a new (blank) database environment"""
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        trigger_and_handle_hook(ctx, HookEvent.PreDbNew, [name])

        try:
            dbenv.new(name, copy_from=None)
            ctx.console.print(
                Panel(
                    f"New environment '{name}' created",
                    title="Creating database environment",
                    title_align="left",
                )
            )
        except FileExistsError:
            raise RiptideCliError("Environment with this name already exists.", ctx)
        except NameError:
            raise RiptideCliError("Invalid name for new environment, do not use special characters", ctx)
        except Exception as ex:
            raise RiptideCliError("Error creating environment", ctx) from ex

        if not stay:
            await switch_impl(ctx, name)

        trigger_and_handle_hook(ctx, HookEvent.PostDbNew, [name])

    @cli_section("Database")
    @main.command(CMD_DB_DROP)
    @click.pass_context
    @click.argument("name")
    def drop(ctx, name):
        """Delete a database environment"""
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        panel = Panel(
            f"Deleting environment '{name}'... this may take a while...",
            title="Deleting database environment",
            title_align="left",
        )
        try:
            with Live(panel, refresh_per_second=5, console=ctx.console):
                dbenv.drop(name)
                panel.renderable = f"Database environment '{name}' deleted."
        except FileNotFoundError:
            raise RiptideCliError("Environment with this name does not exist.", ctx)
        except OSError:
            raise RiptideCliError("Can not delete the environment that is currently active.", ctx)
        except Exception as ex:
            raise RiptideCliError("Error deleting environment", ctx) from ex

    @cli_section("Database")
    @main.command(CMD_DB_COPY)
    @click.pass_context
    @click.option("-s", "--stay", is_flag=True, help="If set, don't switch to the newly created environment.")
    @click.argument("name_to_copy")
    @click.argument("name_new")
    @async_command()
    async def copy(ctx, stay, name_to_copy, name_new):
        """Copy an existing database environment"""
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        trigger_and_handle_hook(ctx, HookEvent.PreDbCopy, [name_to_copy, name_new])

        # 2. Import
        panel = Panel(
            f"Copying from '{escape(name_to_copy)}' to '{escape(name_new)}'... this may take a while...",
            title="Copying database environment",
            title_align="left",
        )
        try:
            with Live(panel, refresh_per_second=5, console=ctx.console):
                dbenv.new(name_new, copy_from=name_to_copy)
                panel.renderable = f"New environment '{name_new}' created"
        except FileExistsError:
            raise RiptideCliError("Environment with this name already exists.", ctx)
        except FileNotFoundError:
            raise RiptideCliError("Environment to copy from not found.", ctx)
        except NameError:
            raise RiptideCliError("Invalid name for new environment, do not use special characters", ctx)
        except Exception as ex:
            raise RiptideCliError("Error creating environment", ctx) from ex

        if not stay:
            await switch_impl(ctx, name_new)

        trigger_and_handle_hook(ctx, HookEvent.PostDbCopy, [name_to_copy, name_new])

    @cli_section("Database")
    @main.command(CMD_DB_IMPORT)
    @click.argument("file")
    @click.pass_context
    @async_command()
    async def importt(ctx, file):
        """
        Import a database dump into the active environment.
        The format of the dump depends on the database driver.
        """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        await importt_impl(ctx, file)

    @cli_section("Database")
    @main.command(CMD_DB_EXPORT)
    @click.argument("file")
    @click.pass_context
    @async_command()
    async def export(ctx, file):
        """
        Export database dump from the current environment.
        The format of the dump depends on the database driver.
        """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)
        assert dbenv.db_service is not None
        db_name = dbenv.db_service["$name"]
        env_name = dbenv.currently_selected_name()
        db_driver = db_driver_for_service.get(dbenv.db_service)
        assert db_driver is not None  # todo: error handling

        # 1. If not running, start database
        was_running = engine.status(project)[db_name]
        if not was_running:
            await start_project(ctx, [db_name], show_status=False)

        trigger_and_handle_hook(ctx, HookEvent.PreDbExport, [env_name])

        # 2. Export
        panel = Panel(f"Exporting from '{env_name}'... this may take a while...", title="Exporting", title_align="left")
        try:
            with Live(panel, refresh_per_second=5, console=ctx.console):
                db_driver.export(engine, file)
                panel.renderable = f"Database environment '{env_name}' exported to '{file}'."
        except FileNotFoundError:
            raise RiptideCliError("Environment does not exist. Create it first with db-create", ctx)
        except Exception as ex:
            raise RiptideCliError("Error exporting environment", ctx) from ex

        trigger_and_handle_hook(ctx, HookEvent.PostDbExport, [env_name, HookHostPathArgument(file)])


async def switch_impl(ctx, name):
    project = ctx.system_config["project"]
    engine = ctx.engine
    dbenv = DbEnvironments(project, engine)
    assert dbenv.db_service is not None
    db_name = dbenv.db_service["$name"]

    trigger_and_handle_hook(ctx, HookEvent.PreDbSwitch, [dbenv.currently_selected_name(), name])

    # 1. If running, stop database
    was_running = engine.status(project)[db_name]
    if was_running:
        await stop_project(ctx, [db_name], show_status=False)

    # 2. Switch environment
    try:
        dbenv.switch(name)
        ctx.console.print(
            Panel(
                f"Environment switched to '{name}'",
                title="Switching database environment",
                title_align="left",
            )
        )
    except FileNotFoundError:
        raise RiptideCliError("Environment does not exist. Create it with db-new or db-copy.", ctx)
    except Exception as ex:
        raise RiptideCliError("Error switching environments", ctx) from ex

    # 3. If was running: start database again
    if was_running:
        await start_project(ctx, [db_name])

    trigger_and_handle_hook(ctx, HookEvent.PostDbSwitch, [name])


async def importt_impl(ctx, file):
    project = ctx.system_config["project"]
    engine = ctx.engine
    dbenv = DbEnvironments(project, engine)
    assert dbenv.db_service is not None
    db_name = dbenv.db_service["$name"]
    env_name = dbenv.currently_selected_name()
    db_driver = db_driver_for_service.get(dbenv.db_service)
    assert db_driver is not None  # todo: error handling

    if not file or file == "":
        raise RiptideCliError("Please specify a path.", ctx)

    if not os.path.exists(os.path.abspath(file)):
        raise RiptideCliError("The path does not exist.", ctx)

    # 1. If not running, start database
    was_running = engine.status(project)[db_name]
    if not was_running:
        await start_project(ctx, [db_name], show_status=False)
        # TODO: Some databases need a while. How to do this better? mysqladmin for example doesn't help :(
        await sleep(15)

    trigger_and_handle_hook(ctx, HookEvent.PreDbImport, [env_name, HookHostPathArgument(file)])

    # 2. Import
    panel = Panel(
        f"Importing into database environment '{env_name}'... this may take a while...",
        title="Importing database environment",
        title_align="left",
    )
    try:
        with Live(panel, refresh_per_second=5, console=ctx.console):
            db_driver.importt(engine, os.path.abspath(file))
            panel.renderable = f"Database environment '{env_name}' imported."

    except FileNotFoundError:
        raise RiptideCliError("Environment does not exist. Create it first with db:create", ctx)
    except Exception as ex:
        raise RiptideCliError("Error importing database environment", ctx) from ex

    trigger_and_handle_hook(ctx, HookEvent.PostDbImport, [env_name, HookHostPathArgument(file)])

    return True
