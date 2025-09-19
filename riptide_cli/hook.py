from typing import IO, Any, Sequence

from click import ClickException, echo
from riptide.hook.additional_volumes import HookHostPathArgument
from riptide.hook.event import AnyHookEvent
from riptide.hook.manager import HookArgument
from riptide_cli.loader import RiptideCliCtx


class EmptyClickException(ClickException):
    def __init__(self, exit_code: int) -> None:
        self.exit_code = exit_code
        super().__init__("")

    def show(self, file: IO[Any] | None = None) -> None:
        pass


def trigger_and_handle_hook(
    ctx: RiptideCliCtx,
    c_event: AnyHookEvent,
    arguments: Sequence[HookArgument],
    additional_host_mounts: dict[str, HookHostPathArgument] | None = None,  # container path -> host path + ro flag
    *,
    cli_hook_prefix: str = "Hook",
    show_error_msg: bool = True,
    nl: bool = True,
):
    if additional_host_mounts is None:
        additional_host_mounts = {}
    ret = ctx.hook_manager.trigger_event_on_cli(
        c_event, arguments, additional_host_mounts, cli_hook_prefix=cli_hook_prefix
    )
    if ret != 0:
        if show_error_msg:
            exc = ClickException("A hook failed")
            exc.exit_code = ret
            raise exc
        raise EmptyClickException(ret)
    if nl:
        echo()
