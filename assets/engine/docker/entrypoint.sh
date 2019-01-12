#!/bin/sh

# redirect stdout and stderr to files
exec >>/riptide_stdout
exec 2>>/riptide_stderr

echo="SERVICE RESTART - $(date) - Thank you for using Riptide!"
echo $echo
>&2 echo $echo

# Start logging commands, prefixed RIPTIDE__DOCKER_CMD_LOGGING_
#/cmd_logs
env | grep -oP '^RIPTIDE__DOCKER_CMD_LOGGING_\K\w+(?==)' | while read -r name ; do
    eval "cmd=\${RIPTIDE__DOCKER_CMD_LOGGING_${name}}"
    sh -c "${cmd}" > /cmd_logs/${name} &
done

# Run original entrypoint and/or cmd
if [ -z "RIPTIDE__DOCKER_DONT_RUN_CMD" ]
then
    # Run entrypoint only directly
    eval $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT
else
    # Run entrypoint (if exists) and command
    eval $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT $@
fi