# To be sourced by a zsh shell
# todo file header
SCRIPTPATH=$(dirname ${(%):-%x})

. "$SCRIPTPATH/common.sh"

if [[ ${chpwd_functions[(I)riptide_cwdir_hook]} -eq 0 ]]; then
  chpwd_functions+=(riptide_cwdir_hook)
fi

riptide_cwdir_hook