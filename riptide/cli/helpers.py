import asyncio
import traceback
from click import style, echo, ClickException
from click._compat import get_text_stderr
from functools import update_wrapper


def get_is_verbose(ctx):
    if hasattr(ctx, "riptide_options"):
        return ctx.riptide_options["verbose"]
    if hasattr(ctx, "parent"):
        if hasattr(ctx.parent, "riptide_options"):
            return ctx.parent.riptide_options["verbose"]
    return True


class RiptideCliError(ClickException):

    def __init__(self, message, ctx):
        super().__init__(message)
        self.ctx = ctx

    def show(self, file=None):
        verbose = get_is_verbose(self.ctx) or file is not None

        if file is None:
            file = get_text_stderr()
        if verbose:
            echo(style(traceback.format_exc(), bg='red'), file=file)
        else:
            echo(style(self.message, bg='red', fg='white', bold=True), file=file)
            if self.__context__ is not None:
                echo(style('>> Error message: %s' % str(self.__context__), bg='red', fg='white'), file=file)
                echo()
                echo(style('Use -v to show stack traces.', fg='yellow'), file=file)


def warn(msg):
    echo(style('Warning: ', fg='yellow', bold=True) + style(msg, fg='yellow'))


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


## SOURCE:  https://github.com/pallets/click/issues/85
def async_command(f):
    f = asyncio.coroutine(f)

    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))

    return update_wrapper(wrapper, f)


TAB = '    '
