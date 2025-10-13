import os

from rich.console import Group, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text
from riptide.config.document.project import Project
from riptide.config.files import get_project_setup_flag_path
from riptide.db.driver import db_driver_for_service
from riptide.db.environments import DbEnvironments
from riptide.hook.event import HookEvent
from riptide_cli.command.db import importt_impl
from riptide_cli.command.importt import files_impl
from riptide_cli.helpers import RiptideCliError, rule
from riptide_cli.hook import trigger_and_handle_hook
from riptide_cli.loader import RiptideCliCtx


async def setup_assistant(ctx: RiptideCliCtx, force: bool, skip: bool):
    assert ctx.system_config is not None
    project = ctx.system_config["project"]
    engine = ctx.engine

    if ctx.project_is_set_up and not force:
        raise RiptideCliError(
            "The project is already set up. If you still want to run this command, pass --force.", ctx
        )

    if skip:
        ctx.console.print("Project was marked as set up.")
        finish(ctx, project, None)
        return

    panel = Panel(
        (
            "Thank you for using Riptide!\n"
            f"This command will guide you through the initial setup for '{project['name']}'.\n"
            "Please follow the instructions carefully, it won't take long!"
        ),
        title="[bold]:water_wave: Welcome!",
        border_style="cyan",
        title_align="left",
    )
    ctx.console.print(panel)
    run_setup = Confirm.ask("[magenta]> Do you wish to run this interactive setup?", default="y", console=ctx.console)

    # Q1: Run?
    if not run_setup:
        ctx.console.print("Okay! To re-run this setup, pass the --force option.")
        finish(ctx, project, False)
        return

    # Q2: New or existing?
    choice_import = Prompt.ask(
        "[magenta]> Are you working on a [bold underline]n[/]ew project that needs to be installed, "
        "or do you want to [bold underline]i[/]mport existing data?",
        choices=["n", "i"],
        default="i",
        console=ctx.console,
    )

    if choice_import == "n":
        # New project
        rule(ctx.console, "# Setting up a new project", characters="=", style="default")
        if "notices" in project["app"] and "installation" in project["app"]["notices"]:
            ctx.console.print(
                f"Please read the following notes on how to run a first-time-installation "
                f"for '{project['app']['name']}'."
            )
            ctx.console.print(
                Panel(
                    escape(project["app"]["notices"]["installation"]),
                    title="Installation instructions",
                    title_align="left",
                )
            )
        else:
            ctx.console.print(
                "This project unfortunately does not provide any information on how to set it up. "
                "You can try checking the README for more information."
            )
        ctx.console.input("[magenta]> Press ENTER to continue...")
        finish(ctx, project, True)
        return

    # Existing project
    rule(ctx.console, "# Setting up an existing project", characters="=", style="default")

    db_can_be_imported = DbEnvironments.has_db(project)
    files_can_be_imported = "import" in project["app"]

    if not db_can_be_imported and not files_can_be_imported:
        # Nothing to import
        ctx.console.print(
            f"The app '{project['app']['name']}' does not specify a database or files to import. You are already done!"
        )
        ctx.console.input("[magenta]> Press ENTER to continue...")
        finish(ctx, project, False)
        return

    # Import db
    if db_can_be_imported:
        dbenv = DbEnvironments(project, engine)
        assert dbenv.db_service is not None
        db_driver = db_driver_for_service.get(dbenv.db_service)
        assert db_driver is not None  # todo: error handling
        rule(ctx.console, "## Importing a database", style="default")
        choice = Confirm.ask(
            f"[magenta]> Do you want to import a database (format {dbenv.db_service['driver']['name']})?",
            console=ctx.console,
        )
        if choice:
            # Import db
            exit_cmd = False
            while not exit_cmd:
                prompt = db_driver.ask_for_import_file().rstrip()
                if prompt.endswith("."):
                    prompt = prompt[:-1] + ":"
                path = ctx.console.input(Text("> " + escape(prompt + " "), style="magenta"))
                try:
                    await importt_impl(ctx, path)
                    exit_cmd = True
                except RiptideCliError as err:
                    ctx.console.print("[white on red]Error: " + str(err))
                    try_again = Confirm.ask("[magenta]> Do you want to try again?", console=ctx.console)
                    if not try_again:
                        exit_cmd = True

        else:
            ctx.console.print("Skipping database import. If you change your mind, run [bold]riptide db:import[/].")

    if files_can_be_imported:
        rule(ctx.console, "## Importing files", style="default")
        for key, entry in project["app"]["import"].items():
            run_import = Confirm.ask(
                f"[magenta]> Do you want to import the file or directory labeled '{entry['name']}' "
                f"to <project>/{entry['target']}?"
            )
            if run_import:
                # Import files
                exit_cmd = False
                while not exit_cmd:
                    path = ctx.console.input(
                        Text("> " + escape("Enter path of files or directory to copy: "), style="magenta")
                    )
                    try:
                        files_impl(ctx, key, path)
                        exit_cmd = True
                    except RiptideCliError as err:
                        ctx.console.print("[white on red]Error: " + str(err))
                        try_again = Confirm.ask("[magenta]> Do you want to try again?", console=ctx.console)
                        if not try_again:
                            exit_cmd = True

    ctx.console.print()
    ctx.console.print("Done importing files.")
    ctx.console.input("[magenta]> Press ENTER to continue...")
    finish(ctx, project, False)


def finish(ctx: RiptideCliCtx, project: Project, was_new_project: bool | None):
    assert ctx.system_config is not None

    if was_new_project is not None:
        trigger_and_handle_hook(ctx, HookEvent.PostSetup, ["new-project" if was_new_project else "existing-project"])

    ctx.console.print()

    start_prefix = "You"

    has_usage = "notices" in project["app"] and "usage" in project["app"]["notices"]
    if has_usage:
        has_usage = True
        start_prefix = "After confirming you have done all the steps in the above-printed usage documentation, you"
        ctx.console.print(
            Panel(project["app"]["notices"]["usage"], title="Project usage instructions", title_align="left")
        )
        ctx.console.print()

    contents: list[RenderableType] = [f"{start_prefix} can now start the project with [bold]riptide start[/]."]
    if has_usage:
        contents.append(
            "If you need to read the usage instructions again later on, you can run [bold]riptide notes[/]."
        )

    contents.append("\nMake sure to also have a look at the project's README file, if it has one.")

    project = ctx.system_config["project"]
    if "commands" in project["app"] and len(project["app"]["commands"]) > 0:
        some_commands_in_project = ", ".join([f"[underline]{x}[/]" for x in project["app"]["commands"].keys()][:3])
        if "RIPTIDE_SHELL_LOADED" not in os.environ:
            contents.append(
                "It seems that the Riptide shell integration is not enabled yet.\n"
                "If you want to set it up, have a look at the manual."
            )
        else:
            contents.append(
                f"If you want to use commands like {some_commands_in_project}, "
                f"leave and re-enter the project directory. "
            )

    panel = Panel(
        Group(*contents),
        title="[bold]:water_wave: Done! Your project is set up!",
        title_align="left",
    )
    ctx.console.print(panel)

    open(get_project_setup_flag_path(project.folder()), "a").close()
