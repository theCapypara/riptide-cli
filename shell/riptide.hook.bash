# To be sourced by a bash shell
# todo file header
SCRIPTPATH=$(dirname "${BASH_SOURCE[0]}")

. "$SCRIPTPATH/common.sh"

riptide_prompt_hook() {
    if [ "$(pwd)" != "$RIPTIDE_BASH_LAST_PWD" ]; then
        RIPTIDE_BASH_LAST_PWD=$(pwd)
        riptide_cwdir_hook
    fi
}

PROMPT_COMMAND="riptide_prompt_hook;"$PROMPT_COMMAND