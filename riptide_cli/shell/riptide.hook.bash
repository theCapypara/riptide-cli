# To be sourced by a bash shell
# Riptide's bash integration
# Works by adding itself to the PROMPT_COMMAND and checking if working directory changed.

SCRIPTPATH=$(dirname "${BASH_SOURCE[0]}")

. "$SCRIPTPATH/riptide.hook.common.sh"

riptide_prompt_hook() {
    if [ "$(pwd)" != "$RIPTIDE_BASH_LAST_PWD" ]; then
        RIPTIDE_BASH_LAST_PWD=$(pwd)
        riptide_cwdir_hook
    fi
}

PROMPT_COMMAND="riptide_prompt_hook;"$PROMPT_COMMAND
