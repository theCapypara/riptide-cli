# todo file header
riptide_cwdir_hook() {
    RIPTIDE_SHELL_LOADED="yes"
    # find the project path by walking up the directory tree until found or / is reached.
    project_path=$(pwd)
    while [[ "$project_path" != "" && ! -e "$project_path/riptide.yml" ]]; do
        project_path=${project_path%/*}
    done
    if [ ! -z "$project_path" ]; then
        if [ -z "$RIPTIDE__SH_BIN_PATH" ]; then
            RIPTIDE__SH_BIN_PATH="$project_path/_riptide/bin/"
            # Add to path
            export PATH="$RIPTIDE__SH_BIN_PATH:$PATH"
        fi
        RIPTIDE_PROJECT_NAME=$(cat "$project_path/_riptide/name")
    else
        if [ ! -z "$RIPTIDE__SH_BIN_PATH" ]; then
            # Remove riptide project bin path from path. Source: https://stackoverflow.com/a/370192
            export PATH=$(echo ${PATH} | awk -v RS=: -v ORS=: "/$(echo $RIPTIDE__SH_BIN_PATH | sed 's/\//\\\//g')/ {next} {print}")
            RIPTIDE__SH_BIN_PATH=""
        fi
        RIPTIDE_PROJECT_NAME=""
    fi
}
