#!/bin/sh
DIR=$(pwd)
if [[ "$VIRTUAL_ENV" != "" ]]
then
  SUDO_PREFIX=""
else
  SUDO_PREFIX="sudo "
fi
# Install configcrunch
git clone git@github.com:Parakoopa/configcrunch.git ../configcrunch
cd ../configcrunch
eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .
# Install LIB
git clone git@github.com:Parakoopa/riptide-lib.git ../lib
cd ../lib
eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .
# Install engine_docker
git clone git@github.com:Parakoopa/riptide-engine-docker.git ../engine-docker
cd ../engine-docker
eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .
# Install db_mysql
git clone git@github.com:Parakoopa/riptide-db-msql.git ../db-msql
cd ../db-msql
eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .
# Install Proxy
git clone git@github.com:Parakoopa/riptide-proxy.git ../proxy
cd ../proxy
eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .
# Install CLI
cd $DIR
eval $SUDO_PREFIX pip install -r requirements.txt && $SUDO_PREFIX pip install -e .