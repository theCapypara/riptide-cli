# To be sourced by a zsh shell
# Riptide's zsh integration
# Works by adding itself to the chpwd_functions.

SCRIPTPATH=$(dirname ${(%):-%x})

. "$SCRIPTPATH/common.sh"

if [[ ${chpwd_functions[(I)riptide_cwdir_hook]} -eq 0 ]]; then
  chpwd_functions+=(riptide_cwdir_hook)
fi

riptide_cwdir_hook

# Autocomplete
# todo: Does not work correctly yet :(
eval "$(_RIPTIDE_COMPLETE=source_zsh riptide)"