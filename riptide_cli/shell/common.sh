# Common file for Riptide's shell integration

# Shell integration script. To be called whenever the working directory changes.
# Always sets the env. variable RIPTIDE_SHELL_LOADED to "yes"
#
# If in project (this or any parent directory contain a riptide.yml:
#  Sets RIPTIDE_PROJECT_NAME to be the name of the current project.
#  Adds the _riptide/bin path of the current project to the PATH
# If not:
#  Undos above changes.
riptide_cwdir_hook() {
    export RIPTIDE_SHELL_LOADED="yes"
    # find the project path by walking up the directory tree until found or / is reached.
    project_path=$(pwd)
    while [[ "$project_path" != "" && ! -e "$project_path/riptide.yml" ]]; do
        project_path=${project_path%/*}
    done
    if [ ! -z "$project_path" ]; then
        # WE ARE IN PROJECT
        new_sh_path="$project_path/_riptide/bin"
        if [ "$RIPTIDE__SH_BIN_PATH" != "$new_sh_path" ]; then
            if [ ! -z "$RIPTIDE__SH_BIN_PATH" ]; then
                # The variable already existed somehow, nested projects?
                riptide_cwdir_hook__remove
            fi
            RIPTIDE__SH_BIN_PATH=$new_sh_path
            # Add to path
            export PATH="$RIPTIDE__SH_BIN_PATH:$PATH"
        fi
        export RIPTIDE_PROJECT_NAME=$(cat "$project_path/_riptide/name" 2> /dev/null)
    else
        # WE ARE NOT IN PROJECT
        if [ ! -z "$RIPTIDE__SH_BIN_PATH" ]; then
            riptide_cwdir_hook__remove
        fi
        export RIPTIDE_PROJECT_NAME=""
    fi
}

riptide_cwdir_hook__remove() {
    # Remove riptide project bin path from path. Source: https://stackoverflow.com/a/370192
    export PATH=$(echo ${PATH} | awk -v RS=: -v ORS=: "/$(echo $RIPTIDE__SH_BIN_PATH | sed 's/\//\\\//g')/ {next} {print}")
    RIPTIDE__SH_BIN_PATH=""
}