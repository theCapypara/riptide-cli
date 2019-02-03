#!/bin/sh
# Riptide Docker entrypoint script.
#
# Responsible for running some important pre-start operations.
# Afterwards runs the original entrypoint and/or command in (more or less) the same way Docker would.
# The original entrypoint may be specified in the environment variable RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT (see below)
# The original command may be specified by being passed as arguments to this script.
#
# Behaviour is controlled by environment variables.
#
# RIPTIDE__DOCKER_NO_STDOUT_REDIRECT:
#   If set, Riptide will NOT redirect all stdout/stderr output to /riptide_stdout or /riptide_stderr respectively
#
# RIPTIDE__DOCKER_USER:
#   If set, Riptide will try to create a user named "riptide" with this id.
#
# RIPTIDE__DOCKER_GROUP:
#   If this and RIPTIDE__DOCKER_USER are set,
#   Riptide will try to add a group with this id (named riptide; only if not already exists)
#   and add $RIPTIDE__DOCKER_USER to this group.
#
# RIPTIDE__DOCKER_RUN_MAIN_CMD_AS_USER:
#   If set, the original entrypoint and command are run via the $RIPTIDE__DOCKER_USER user using su.
#
# RIPTIDE__DOCKER_DONT_RUN_CMD:
#   If set, the command is not run, only the original entrypoint/nothing.
#
# RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT:
#   Contains the original entrypoint. Can be empty. Will be run and get the command passed
#   (if RIPTIDE__DOCKER_DONT_RUN_CMD is not set)
#
# RIPTIDE__DOCKER_CMD_LOGGING_*:
#   Command logging.
#   All the vlaues of these environment variables will be started and their stdout redirected to /cmd_logs/*.

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
if [ ! -z "$RIPTIDE__DOCKER_USER" ]; then
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
    if ! getent passwd $RIPTIDE__DOCKER_USER > /dev/null; then
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
        usermod -a -G $RIPTIDE__DOCKER_GROUP $USERNAME 2> /dev/null # usermod might not exist, in this case we are out of luck :(
        # Symlink the other user directory to /home/riptide
        mkdir -p /home
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
POSSIBLE_IP=$(getent hosts host.docker.internal | awk '{ print $1 }')
if [ ! -z "$POSSIBLE_IP" ]; then
    # windows + mac
    echo "$POSSIBLE_IP  host.riptide.internal "  >> /etc/hosts
else
    # linux
    echo "172.17.0.1  host.riptide.internal "  >> /etc/hosts
fi


# Run original entrypoint and/or cmd
if [ -z "RIPTIDE__DOCKER_DONT_RUN_CMD" ]; then
    # Run entrypoint only directly
    eval exec $SU_PREFIX $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT $SU_POSTFIX
else
    # Run entrypoint (if exists) and command
    eval exec $SU_PREFIX $RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT $@ $SU_POSTFIX
fi
