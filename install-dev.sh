#!/bin/sh
DIR=$(pwd)

echo "Welcome to the Riptide update and/or installation. Is sudo required to run pip commands? [y/N]"
read yn
case $yn in
    [Yy]* ) SUDO_PREFIX="sudo "; break;;
    * )     SUDO_PREFIX=""
esac

eval $SUDO_PREFIX pip uninstall riptide > /dev/null # old name

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
        git clone git@github.com:Parakoopa/$git_name.git ../$dir_name
        cd ../$dir_name
    fi
    eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .
}

# Install all other riptide components
check_and_pull configcrunch     configcrunch
check_and_pull lib              riptide-lib
check_and_pull engine-docker    riptide-engine-docker
check_and_pull db-mysql         riptide-db-mysql
check_and_pull proxy            riptide-proxy

# Install CLI
echo "----"
echo "INSTALLING riptide-cli"
echo "----"
cd $DIR
eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .