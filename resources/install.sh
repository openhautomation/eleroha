#!/bin/bash
PROGRESS_FILE=/tmp/dependancy_eleroha_in_progress
if [ ! -z $1 ]; then
	PROGRESS_FILE=$1
fi
touch ${PROGRESS_FILE}
echo 0 > ${PROGRESS_FILE}
echo "********************************************************"
echo "*        Installation des dépendances [eleroha]        *"
echo "********************************************************"
apt-get update
echo 50 > ${PROGRESS_FILE}
apt-get install -y python3
apt-get install -y python3-serial python3-requests python3-pyudev
echo 100 > ${PROGRESS_FILE}
echo "********************************************************"
echo "*           Installation terminée [eleroha]            *"
echo "********************************************************"
rm ${PROGRESS_FILE}
