import os

import click
from click import style, echo

from riptide_cli.helpers import cli_section, TAB, RiptideCliError, async_command
from riptide_cli.lifecycle import status_project, stop_project, start_project
from riptide.db.driver import db_driver_for_service
from riptide.db.environments import DbEnvironments


def load(ctx):
    """Adds all database commands to the CLI, if database management is available"""
    if "project" in ctx.system_config and DbEnvironments.has_db(ctx.system_config["project"]):
        ctx.command.add_command(status,  'db-status')
        ctx.command.add_command(lst,     'db-list')
        ctx.command.add_command(switch,  'db-switch')
        ctx.command.add_command(new,     'db-new')
        ctx.command.add_command(drop,    'db-drop')
        ctx.command.add_command(copy,    'db-copy')
        ctx.command.add_command(importt, 'db-import')
        ctx.command.add_command(export,  'db-export')


@cli_section("Database")
@click.command()
@click.pass_context
def status(ctx):
    """ Status of database service and active environment """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
    dbenv = DbEnvironments(project, engine)

    current = dbenv.currently_selected_name()

    echo("Currently active database environment: " + style(current, bold=True))
    echo()
    status_project(ctx, limit_services=[dbenv.db_service["$name"]])


@cli_section("Database")
@click.command()
@click.pass_context
def lst(ctx):
    """ Lists database environments """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
    dbenv = DbEnvironments(project, engine)

    current = dbenv.currently_selected_name()

    echo("Database environments: ")

    for env in dbenv.list():
        if env == current:
            echo(TAB + "- " + style(env, bold=True) + " [Current]")
        else:
            echo(TAB + "- " + env)

    echo()
    echo("Use db:switch to switch environments.")


@cli_section("Database")
@click.command()
@click.pass_context
@click.argument('name')
@async_command
async def switch(ctx, name):
    """ Switches the active database environment """
    await switch_impl(ctx, name)


async def switch_impl(ctx, name):
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
    dbenv = DbEnvironments(project, engine)
    db_name = dbenv.db_service["$name"]

    # 1. If running, stop database
    was_running = engine.status(project, ctx.parent.system_config)[db_name]
    if was_running:
        await stop_project(ctx, [db_name], show_status=False)

    # 2. Switch environment
    try:
        dbenv.switch(name)
        echo()
        echo("Environment switched to: " + style(name, bold=True))
        echo()
    except FileNotFoundError:
        raise RiptideCliError("Environment does not exist. Create it with db:new or db:copy.", ctx)
    except Exception as ex:
        raise RiptideCliError("Error switching environments", ctx) from ex

    # 3. If was running: start database again
    if was_running:
        await start_project(ctx, [db_name])


@cli_section("Database")
@click.command()
@click.pass_context
@click.option('-s', '--stay', is_flag=True, help="If set, don't switch to the newly created environment.")
@click.argument('name')
@async_command
async def new(ctx, stay, name):
    """ Create a new (blank) database environment """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
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
@click.command()
@click.pass_context
@click.argument('name')
def drop(ctx, name):
    """ Delete a database environment """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
    dbenv = DbEnvironments(project, engine)

    echo("Deleting... this may take a while...")
    try:
        dbenv.drop(name)
        echo()
        echo("Environment deleted: " + style(name, bold=True))
        echo()
    except FileNotFoundError:
        raise RiptideCliError("Envrionment with this name does not exist.", ctx)
    except EnvironmentError:
        raise RiptideCliError("Can not delete the environment that is currently active.", ctx)
    except Exception as ex:
        raise RiptideCliError("Error deleting environment", ctx) from ex


@cli_section("Database")
@click.command()
@click.pass_context
@click.option('-s', '--stay', is_flag=True, help="If set, don't switch to the newly created environment.")
@click.argument('name_to_copy')
@click.argument('name_new')
@async_command
async def copy(ctx, stay, name_to_copy, name_new):
    """ Copy an existing database environment """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
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
@click.command()
@click.argument('file')
@click.pass_context
@async_command
async def importt(ctx, file):
    """
    Import a database dump into the active environment.
    The format of the dump depends on the database driver.
    """
    await importt_impl(ctx, file)


async def importt_impl(ctx, file):
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
    dbenv = DbEnvironments(project, engine)
    db_name = dbenv.db_service["$name"]
    env_name = dbenv.currently_selected_name()
    db_driver = db_driver_for_service.get(dbenv.db_service)

    if not file or file == "":
        raise RiptideCliError("Please specify a path.", ctx)

    if not os.path.exists(os.path.abspath(file)):
        raise RiptideCliError("The path does not exist.", ctx)

    # 1. If not running, start database
    was_running = engine.status(project, ctx.parent.system_config)[db_name]
    if not was_running:
        await start_project(ctx, [db_name], show_status=False)

    # 2. Import
    echo("Importing into database environment %s... this may take a while..." % env_name)
    try:
        db_driver.importt(engine, os.path.abspath(file))
        echo()
        echo("Database environment %s imported." % env_name)
        echo()
        return True
    except FileNotFoundError:
        raise RiptideCliError("Environment does not exist. Create it first with db:create", ctx)
    except Exception as ex:
        raise RiptideCliError("Error importing database environment", ctx) from ex


@cli_section("Database")
@click.command()
@click.argument('file')
@click.pass_context
@async_command
async def export(ctx, file):
    """
    Export database dump from the current environment.
    The format of the dump depends on the database driver.
    """
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine
    dbenv = DbEnvironments(project, engine)
    db_name = dbenv.db_service["$name"]
    env_name = dbenv.currently_selected_name()
    db_driver = db_driver_for_service.get(dbenv.db_service)

    # 1. If not running, start database
    was_running = engine.status(project, ctx.parent.system_config)[db_name]
    if not was_running:
        await start_project(ctx, [db_name], show_status=False)

    # 2. Export
    echo("Exporting from %s... this may take a while..." % env_name)
    try:
        db_driver.export(engine, os.path.abspath(file))
        echo()
        echo("Environment %s exported." % env_name)
        echo()
    except FileNotFoundError:
        raise RiptideCliError("Environment does not exist. Create it first with db:create", ctx)
    except Exception as ex:
        raise RiptideCliError("Error exporting environment", ctx) from ex
