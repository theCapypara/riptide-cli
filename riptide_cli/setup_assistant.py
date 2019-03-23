import os
from sys import stdin

from click import style, echo, getchar

from riptide_cli.command.db import importt_impl
from riptide_cli.command.importt import files_impl
from riptide_cli.helpers import RiptideCliError, TAB, header
from riptide.config.files import get_project_setup_flag_path
from riptide.db.driver import db_driver_for_service
from riptide.db.environments import DbEnvironments


CMD_SEP = style('-----', fg='cyan')


async def setup_assistant(ctx, force, skip):
    project = ctx.parent.system_config["project"]
    engine = ctx.parent.engine

    if ctx.parent.project_is_set_up and not force:
        raise RiptideCliError("The project is already set up. If you still want to run this command, pass --force.",
                              ctx)

    if skip:
        echo("Project was marked as set up.")
        finish(ctx)
        return

    echo(style("Thank you for using Riptide!", fg='cyan', bold=True))
    echo("This command will guide you through the initial setup for %s." % project["name"])
    echo(style("Please follow it very carefully, it won't take long!", bold=True))
    echo(style("> Press any key to continue...", fg='magenta'))
    getchar()
    echo()
    echo(header("> BEGIN SETUP"))
    if "notices" in project["app"] and "usage" in project["app"]["notices"]:
        echo()
        echo(style("Usage notes for running %s" % project["app"]["name"], bold=True) + " with Riptide:")
        echo(TAB + TAB.join(project["app"]["notices"]["usage"].splitlines(True)))
    echo()

    # Q1
    echo(style("> Do you wish to run this interactive setup? [Y/n] ", fg='magenta'), nl=False)
    if getchar(True).lower() == 'n':
        echo()
        echo()
        echo(header("> END SETUP"))
        echo("Okay! To re-run this setup, pass the --force option.")
        finish(ctx)
        return
    echo()
    echo()
    echo(header("> INTERACTIVE SETUP"))

    # Q2: New or existing?
    echo(style("> Are you working on a ", fg='magenta') +
         style("n", bold=True, fg="cyan") +
         style("ew project that needs to be installed or do you want to ", fg='magenta') +
         style("I", bold=True, fg="cyan") +
         style("mport existing data? [n/I] ", fg='magenta'), nl=False)
    if getchar(True).lower() == 'n':
        # New project
        if "notices" in project["app"] and "installation" in project["app"]["notices"]:
            echo()
            echo()
            echo(header("> NEW PROJECT"))
            echo("Okay! Riptide can't guide you through the installation automatically.")
            echo("Please read these notes on how to run a first-time-installation for %s." % project["app"]["name"])
            echo()
            echo(style("Installation instructions:", bold=True))
            echo(TAB + TAB.join(project["app"]["notices"]["installation"].splitlines(True)))
            finish(ctx)
            return

    # Existing project
    echo()
    echo()
    echo(header("> EXISTING PROJECT"))

    db_can_be_imported = DbEnvironments.has_db(project)
    files_can_be_imported = 'import' in project['app']

    if not db_can_be_imported and not files_can_be_imported:
        # Nothing to import
        echo("The app %s does not specify a database or files to import. You are already done!" % project["app"]["name"])
        finish(ctx)
        return

    # Import db
    if db_can_be_imported:
        dbenv = DbEnvironments(project, engine)
        db_driver = db_driver_for_service.get(dbenv.db_service)
        echo(TAB + header("> DATABASE IMPORT"))
        echo(style("> Do you want to import a database (format %s)? [Y/n] " % dbenv.db_service['driver']['name'],
                   fg='magenta'), nl=False)
        if getchar(True).lower() != 'n':
            # Import db
            echo()
            exit_cmd = False
            while not exit_cmd:
                echo(db_driver.ask_for_import_file() + " ", nl=False)
                path = stdin.readline().rstrip('\r\n')
                try:
                    echo(CMD_SEP)
                    await importt_impl(ctx, path)
                    exit_cmd = True
                    echo(CMD_SEP)
                except RiptideCliError as err:
                    echo("Error: " + style(str(err), fg='red'))
                    echo(CMD_SEP)
                    echo(style("> Do you want to try again? [y/N] ", fg='magenta'), nl=False)
                    if getchar(True).lower() != 'y':
                        exit_cmd = True
                    echo()

        else:
            echo()
            echo("Skipping database import. If you change your mind, run db:import.")

    if files_can_be_imported:
        echo(TAB + header("> FILE IMPORT"))
        for key, entry in project['app']['import'].items():
            echo(TAB + TAB + header(("> %s IMPORT" % key)))
            echo(style("> Do you wish to import %s to <project>/%s? [Y/n] " % (entry['name'], entry['target'])
                       , fg='magenta'), nl=False)
            if getchar(True).lower() != 'n':
                # Import files
                echo()
                exit_cmd = False
                while not exit_cmd:
                    echo("Enter path of files or directory to copy: ", nl=False)
                    path = stdin.readline().rstrip('\r\n')
                    try:
                        echo(CMD_SEP)
                        files_impl(ctx, key, path)
                        exit_cmd = True
                        echo(CMD_SEP)
                    except RiptideCliError as err:
                        echo("Error: " + style(str(err), fg='red'))
                        echo(CMD_SEP)
                        echo(style("> Do you want to try again? [y/N] ", fg='magenta'), nl=False)
                        if getchar(True).lower() != 'y':
                            exit_cmd = True
                        echo()
            else:
                echo()
    echo()
    echo(header("> IMPORT DONE!", bold=True))
    echo("All files were imported.")
    finish(ctx)


def finish(ctx):
    echo()
    echo(style("DONE!", bold=True))
    echo()
    echo("You can now start the project with start, "
         "if the usage instructions at the beginning don't require you to do anything else.")
    echo("If you need to read those again run " + style("riptide notes", bold=True))
    echo()
    project = ctx.parent.system_config["project"]
    if "commands" in project["app"]:
        cmd = list(project["app"]["commands"].keys())[0]
        some_commands_in_project = ", ".join(list(project["app"]["commands"].keys())[:3])
        if 'RIPTIDE_SHELL_LOADED' not in os.environ:
            echo("It seems that the Riptide shell integration is not enabled yet.")
            echo("It is available for Bash and Zsh and allows you to run custom commands such as %s more easily."
                 % some_commands_in_project)
            echo("If you want to set it up, have a look at the manual.")
        else:
            echo("If you want to use commands like %s leave and re-enter the project directory. " % some_commands_in_project)

        echo("You don't need to use 'riptide cmd' then: '%s cmd %s arg1 arg2' -> '%s arg1 arg2'"
             % (style("riptide", bold=True), cmd, style(cmd, bold=True)))
    open(get_project_setup_flag_path(project.folder()), 'a').close()
