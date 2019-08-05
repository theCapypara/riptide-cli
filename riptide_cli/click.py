"""Click extension module"""

# TODO: Colored subcommand help
from click import Option, Command
from click_help_colors import HelpColorsGroup


class ClickMainGroup(HelpColorsGroup):
    """
    Special group class that allows grouping subcommands into sections using the @cli_section annotation.
    """
    # Allow parsing all sub parameters, even those passed to sub commands
    allow_interspersed_args = True
    ignore_unknown_options = True

    def __init__(self, *args, **kwargs):
        # Dedicated help option not supported for this group because of the way it would catch subcommand help options.
        super().__init__(*args, **kwargs, add_help_option=False)

    def invoke(self, ctx):
        """'Fix' for Click not reading the '--version' or '--rename' flag without a sub command."""
        if not ctx.protected_args and (("version" in ctx.params and ctx.params["version"]) or ("rename" in ctx.params and ctx.params["rename"])):
            return Command.invoke(self, ctx)
        return super().invoke(ctx)

    def format_commands(self, ctx, formatter):
        """
        Like multi command's version, but also grouping commands into subsections, if available.
        """
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            sections = {}
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                if not hasattr(cmd, 'riptide_section'):
                    cmd.riptide_section = 'General'
                if cmd.riptide_section not in sections:
                    sections[cmd.riptide_section] = []
                sections[cmd.riptide_section].append((subcommand, help))

            for section_name, rows in sections.items():
                with formatter.section(section_name + ' Commands'):
                    # Make sure the spacing between comamnd and help text is always the same, across all sections.
                    spacing = (formatter.width - 6 - max(len(cmd[0]) for cmd in rows)) - limit + 2
                    formatter.write_dl(rows, col_spacing=spacing)
