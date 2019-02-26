#!/bin/sh
DIR=$(pwd)

echo "Welcome to the Riptide update and/or installation. Is sudo required to run pip commands? [y/N]"
read yn
case $yn in
    [Yy]* ) SUDO_PREFIX="sudo "; break;;
    * )     SUDO_PREFIX=""
esac

eval $SUDO_PREFIX pip3 uninstall riptide > /dev/null # old name

check_and_pull() {
    dir_name=$1
    git_name=$2

    echo "----"
    echo "INSTALLING $git_name"
    echo "----"

    if [ -d "../$dir_name" ]; then
        # update
        cd ../$dir_name
        git pull
    else
        # clone
        git clone ssh://git@k4101.pixsoftware.de:7999/riptide/$git_name.git ../$dir_name
        cd ../$dir_name
    fi
    eval $SUDO_PREFIX pip3 install -r requirements.txt && $SUDO_PREFIX pip3 install -e .
}

# Install all other riptide components
check_and_pull configcrunch     configcrunch
check_and_pull lib              lib
check_and_pull engine-docker    engine-docker
check_and_pull db-mysql         db-mysql
check_and_pull proxy            proxy

# Install CLI
echo "----"
echo "INSTALLING riptide-cli"
echo "----"
cd $DIR
eval $SUDO_PREFIX pip3 install -r requirements.txt && $SUDO_PREFIX pip3 install -e .
