#!/bin/sh
# todo file header

if [ -z "$RIPTIDE__DOCKER_NO_STDOUT_REDIRECT" ]
then
    # redirect stdout and stderr to files
    exec >>/riptide_stdout
    exec 2>>/riptide_stderr

    echo="SERVICE RESTART - $(date) - Thank you for using Riptide!"
    echo $echo
    >&2 echo $echo
fi

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
    # ADD GROUP
    if ! grep -q $RIPTIDE__DOCKER_GROUP /etc/group; then
        # groupadd might be called addgroup (alpine)
        if command -v groupadd > /dev/null; then
            groupadd -g $RIPTIDE__DOCKER_GROUP riptide
        else
            addgroup -g $RIPTIDE__DOCKER_GROUP riptide
        fi
    fi
    GROUP_NAME=$(getent group $RIPTIDE__DOCKER_GROUP  | awk -F\: '{ print $1 }' )
    # ADD USER
    if ! getent passwd $RIPTIDE__DOCKER_USER; then
        USERNAME="riptide"
        # useradd might be called adduser (alpine)
        if command -v useradd > /dev/null; then
            useradd -ms /bin/sh --home-dir /home/riptide -u $RIPTIDE__DOCKER_USER -g $GROUP_NAME riptide 2> /dev/null
        else
            adduser -s /bin/sh -h /home/riptide -u $RIPTIDE__DOCKER_USER -G $GROUP_NAME -D riptide 2> /dev/null
        fi
    else
        # User already exists
        USERNAME=$(getent passwd "$RIPTIDE__DOCKER_USER" | cut -d: -f1)
        HOME_DIR=$(eval echo "~$USERNAME")
        usermod -a -G $RIPTIDE__DOCKER_GROUP $USERNAME
        # Symlink the other user directory to /home/riptide
        ln -s $HOME_DIR /home/riptide
    fi
    # PREPARE SU COMMAND AND ENV
    if [ ! -z "$RIPTIDE__DOCKER_RUN_MAIN_CMD_AS_USER" ]; then
        SU_PREFIX="su $USERNAME -m -c '"
        SU_POSTFIX="'"
        export HOME=/home/riptide
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
