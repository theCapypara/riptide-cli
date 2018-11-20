import traceback
from click import style, echo, ClickException
from click._compat import get_text_stderr


class RiptideCliError(ClickException):

    def __init__(self, message, ctx):
        super().__init__(message)
        self.ctx = ctx

    def show(self, file=None):
        verbose = self.ctx.riptide_options["verbose"] or file is not None

        if file is None:
            file = get_text_stderr()
        if verbose:
            echo(style(traceback.format_exc(), fg='red'), file=file)
        else:
            echo(style(self.message, bg='red', fg='white', bold=True), file=file)
            echo(style('>> Error message: %s' % str(self.__context__), bg='red', fg='white'), file=file)
            echo()
            echo(style('Use -v to show stack traces.', fg='yellow'), file=file)


def warn(msg):
    echo(style('Warning: ', fg='yellow', bold=True) + style(msg, fg='yellow'))
