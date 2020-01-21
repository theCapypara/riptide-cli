import os

import click
from asyncio import sleep
from click import style, echo

from riptide_cli.command.constants import CMD_DB_LIST, CMD_DB_SWITCH, CMD_DB_NEW, CMD_DB_DROP, CMD_DB_COPY, \
    CMD_DB_IMPORT, CMD_DB_STATUS, CMD_DB_EXPORT
from riptide_cli.helpers import cli_section, TAB, RiptideCliError, async_command
from riptide_cli.lifecycle import stop_project, start_project
from riptide.db.driver import db_driver_for_service
from riptide.db.environments import DbEnvironments
from riptide_cli.loader import cmd_constraint_project_loaded, load_riptide_core


def cmd_constraint_has_db(ctx):
    cmd_constraint_project_loaded(ctx)
    if not DbEnvironments.has_db(ctx.system_config["project"]):
        raise RiptideCliError("The project doesn't have a service with the role 'db'. "
                              "This is required to use this command.", ctx)


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
        db_driver = db_driver_for_service.get(dbenv.db_service)

        running = engine.service_status(project, dbenv.db_service["$name"])

        if running:
            echo(f"{'Status':<20}: " + style("Running", bold=True, fg="green"))
        else:
            echo(f"{'Status':<20}: " + style("Not running", bold=True, fg="red"))

        for key,label in db_driver.collect_info().items():
            echo(f"{key:<20}: {label}")

        current = dbenv.currently_selected_name()
        echo("Active environment  : " + style(current, bold=True))


    @cli_section("Database")
    @main.command(CMD_DB_LIST)
    @click.pass_context
    def lst(ctx):
        """ Lists database environments """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        current = dbenv.currently_selected_name()

        echo("Database environments: ")

        for env in dbenv.list():
            if env == current:
                echo(TAB + "- " + style(env, bold=True) + " [Current]")
            else:
                echo(TAB + "- " + env)

        echo()
        echo("Use db-switch to switch environments.")

    @cli_section("Database")
    @main.command(CMD_DB_SWITCH)
    @click.pass_context
    @click.argument('name')
    @async_command()
    async def switch(ctx, name):
        """ Switches the active database environment """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        await switch_impl(ctx, name)

    @cli_section("Database")
    @main.command(CMD_DB_NEW)
    @click.pass_context
    @click.option('-s', '--stay', is_flag=True, help="If set, don't switch to the newly created environment.")
    @click.argument('name')
    @async_command()
    async def new(ctx, stay, name):
        """ Create a new (blank) database environment """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        try:
            dbenv.new(name, copy_from=None)
            echo()
            echo("New environment created: " + style(name, bold=True))
            echo()
        except FileExistsError:
            raise RiptideCliError("Envrionment with this name already exists.", ctx)
        except NameError:
            raise RiptideCliError("Invalid name for new environment, do not use special characters", ctx)
        except Exception as ex:
            raise RiptideCliError("Error creating environment", ctx) from ex

        if not stay:
            await switch_impl(ctx, name)

    @cli_section("Database")
    @main.command(CMD_DB_DROP)
    @click.pass_context
    @click.argument('name')
    def drop(ctx, name):
        """ Delete a database environment """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        echo("Deleting... this may take a while...")
        try:
            dbenv.drop(name)
            echo()
            echo("Environment deleted: " + style(name, bold=True))
            echo()
        except FileNotFoundError:
            raise RiptideCliError("Envrionment with this name does not exist.", ctx)
        except OSError:
            raise RiptideCliError("Can not delete the environment that is currently active.", ctx)
        except Exception as ex:
            raise RiptideCliError("Error deleting environment", ctx) from ex

    @cli_section("Database")
    @main.command(CMD_DB_COPY)
    @click.pass_context
    @click.option('-s', '--stay', is_flag=True, help="If set, don't switch to the newly created environment.")
    @click.argument('name_to_copy')
    @click.argument('name_new')
    @async_command()
    async def copy(ctx, stay, name_to_copy, name_new):
        """ Copy an existing database environment """
        load_riptide_core(ctx)
        cmd_constraint_has_db(ctx)

        project = ctx.system_config["project"]
        engine = ctx.engine
        dbenv = DbEnvironments(project, engine)

        echo("Copying... this may take a while...")
        try:
            dbenv.new(name_new, copy_from=name_to_copy)
            echo()
            echo("New environment created: " + style(name_new, bold=True))
            echo()
        except FileExistsError:
            raise RiptideCliError("Envrionment with this name already exists.", ctx)
        except FileNotFoundError:
            raise RiptideCliError("Envrionment to copy from not found.", ctx)
        except NameError:
            raise RiptideCliError("Invalid name for new environment, do not use special characters", ctx)
        except Exception as ex:
            raise RiptideCliError("Error creating environment", ctx) from ex

        if not stay:
            await switch_impl(ctx, name_new)

    @cli_section("Database")
    @main.command(CMD_DB_IMPORT)
    @click.argument('file')
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
    @click.argument('file')
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
        db_name = dbenv.db_service["$name"]
        env_name = dbenv.currently_selected_name()
        db_driver = db_driver_for_service.get(dbenv.db_service)

        # 1. If not running, start database
        was_running = engine.status(project)[db_name]
        if not was_running:
            await start_project(ctx, [db_name], show_status=False)

        # 2. Export
        echo(f"Exporting from {env_name}... this may take a while...")
        try:
            db_driver.export(engine, os.path.abspath(file))
            echo()
            echo(f"Environment {env_name} exported.")
            echo()
        except FileNotFoundError:
            raise RiptideCliError("Environment does not exist. Create it first with db-create", ctx)
        except Exception as ex:
            raise RiptideCliError("Error exporting environment", ctx) from ex


async def switch_impl(ctx, name):
    project = ctx.system_config["project"]
    engine = ctx.engine
    dbenv = DbEnvironments(project, engine)
    db_name = dbenv.db_service["$name"]

    # 1. If running, stop database
    was_running = engine.status(project)[db_name]
    if was_running:
        await stop_project(ctx, [db_name], show_status=False)

    # 2. Switch environment
    try:
        dbenv.switch(name)
        echo()
        echo("Environment switched to: " + style(name, bold=True))
        echo()
    except FileNotFoundError:
        raise RiptideCliError("Environment does not exist. Create it with db-new or db-copy.", ctx)
    except Exception as ex:
        raise RiptideCliError("Error switching environments", ctx) from ex

    # 3. If was running: start database again
    if was_running:
        await start_project(ctx, [db_name])


async def importt_impl(ctx, file):
    project = ctx.system_config["project"]
    engine = ctx.engine
    dbenv = DbEnvironments(project, engine)
    db_name = dbenv.db_service["$name"]
    env_name = dbenv.currently_selected_name()
    db_driver = db_driver_for_service.get(dbenv.db_service)

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

    # 2. Import
    echo(f"Importing into database environment {env_name}... this may take a while...")
    try:
        db_driver.importt(engine, os.path.abspath(file))
        echo()
        echo(f"Database environment {env_name} imported.")
        echo()
        return True
    except FileNotFoundError:
        raise RiptideCliError("Environment does not exist. Create it first with db:create", ctx)
    except Exception as ex:
        raise RiptideCliError("Error importing database environment", ctx) from ex
