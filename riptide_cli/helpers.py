import asyncio
import traceback
from click import style, echo, ClickException
from click._compat import get_text_stderr
from functools import update_wrapper

from schema import SchemaError


def get_is_verbose(ctx):
    """Returns whether or not verbose mode is enabled"""
    if hasattr(ctx, "riptide_options"):
        return ctx.riptide_options["verbose"]
    if hasattr(ctx, "parent"):
        if hasattr(ctx.parent, "riptide_options"):
            return ctx.parent.riptide_options["verbose"]
    return True


class RiptideCliError(ClickException):
    """Custom error class for displaying errors in the Riptide CLI"""
    def __init__(self, message, ctx):
        super().__init__(message)
        self.ctx = ctx

    def show(self, file=None):
        if self.ctx.resilient_parsing:
            return
        verbose = get_is_verbose(self.ctx) or file is not None

        if file is None:
            file = get_text_stderr()
        if verbose:
            echo(style(traceback.format_exc(), bg='red'), file=file)
        else:
            echo(style(self.message, bg='red', fg='white', bold=True), file=file)
            current_err = self
            previous_message = str(self)
            while current_err.__context__ is not None:
                current_err = current_err.__context__
                # Filter duplicate exception messages. 'schema' used by configcrunch does that for example.
                if previous_message != str(current_err):
                    echo(style(f'>> Caused by: {str(current_err)}', bg='red', fg='white'), file=file)
                previous_message = str(current_err)
            echo()
            echo(style('Use -v to show stack traces.', fg='yellow'), file=file)

    def __str__(self):
        error_string = self.__class__.__name__ + ": " + self.message
        if self.__cause__:
            error_string += ": " + self.__cause__.__class__.__name__ + ": " + str(self.__cause__)
        return error_string


def warn(msg, with_prefix=True):
    echo((style('Warning: ', fg='yellow', bold=True) if with_prefix else "") + style(msg, fg='yellow'))


def cli_section(section):
    """
    Assigns commands to a section. Must be added as an annotation to commands,
    and therefor BEFORE the @click.command.
    :param section:
    :return:
    """
    def decorator(f):
        f.riptide_section = section
        return f
    return decorator


def async_command(interrupt_handler=lambda _, __: True):
    """
    Makes a Click command be wrapped inside the execution of an asyncio loop
    SOURCE:  https://github.com/pallets/click/issues/85
    """
    def decorator(f):
        f = asyncio.coroutine(f)

        def wrapper(ctx, *args, **kwargs):
            loop = asyncio.get_event_loop()
            try:
                return loop.run_until_complete(f(ctx, *args, **kwargs))
            except (KeyboardInterrupt, SystemExit) as ex:
                interrupt_handler(ctx, ex)

        return update_wrapper(wrapper, f)
    return decorator


def header(msg, bold=False):
    """Uniform header style"""
    return style(msg, bg='cyan', fg='white', bold=bold)


TAB = '    '
