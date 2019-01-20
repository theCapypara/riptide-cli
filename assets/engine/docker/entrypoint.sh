#!/bin/sh
# todo file header

# redirect stdout and stderr to files
exec >>/riptide_stdout
exec 2>>/riptide_stderr

echo="SERVICE RESTART - $(date) - Thank you for using Riptide!"
echo $echo
>&2 echo $echo

# Start logging commands, prefixed RIPTIDE__DOCKER_CMD_LOGGING_
env | sed -n "s/^RIPTIDE__DOCKER_CMD_LOGGING_\(\S*\)=.*/\1/p" | while read -r name ; do
    eval "cmd=\${RIPTIDE__DOCKER_CMD_LOGGING_${name}}"
    # XXX: Currently waiting 5sec for service to start, make configurable?
    sh -c "sleep 5; ${cmd}" > /cmd_logs/${name} &
done

# Change the user if requested
SU_PREFIX=""
SU_POSTFIX=""
if [ ! -z "$RIPTIDE__DOCKER_USER" ]
then
    if ! grep -q $RIPTIDE__DOCKER_GROUP /etc/group; then
        groupadd -g $RIPTIDE__DOCKER_GROUP riptide
    fi
    if ! getent passwd $RIPTIDE__DOCKER_USER; then
        USERNAME="riptide"
        useradd -ms /bin/sh -u $RIPTIDE__DOCKER_USER -g $RIPTIDE__DOCKER_GROUP riptide
    else
        USERNAME=$(getent passwd "$RIPTIDE__DOCKER_USER" | cut -d: -f1)
        usermod -a -G $RIPTIDE__DOCKER_GROUP $USERNAME
    fi
    if [ ! -z "$RIPTIDE__DOCKER_RUN_MAIN_CMD_AS_ROOT" ]; then
        SU_PREFIX="su $USERNAME -m -c '"
        SU_POSTFIX="'"
    fi
fi

# host.riptide.internal is supposed to be routable to the host.
# windows + mac
POSSIBLE_IP=$(getent hosts host.docker.internal | awk '{ print $1 }')
if [ ! -z "$POSSIBLE_IP" ]
then
    echo "$POSSIBLE_IP  host.riptide.internal "  >> /etc/hosts
else
    # linux
    echo "172.17.0.1  host.riptide.internal "  >> /etc/hosts
fi

# Run original entrypoint and/or cmd
if [ -z "RIPTIDE__DOCKER_DONT_RUN_CMD" ]
then
    # Run entrypoint only directly
    eval exec $SU_PREFIX $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT $SU_POSTFIX
else
    # Run entrypoint (if exists) and command
    eval exec $SU_PREFIX $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT $@ $SU_POSTFIX
fi
