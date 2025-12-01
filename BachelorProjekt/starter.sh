#!/bin/bash
# Starts an experiment
#

# print help 
if [[ $1 == "--help" || $1 == "-h" ]]; then
    echo "Usage: . starter.sh [options]"
    echo "Options:"
    echo "--reset    or -r  : will reset everything blockchain related"
    echo "--start    or -s  : will start the experiment"
    echo "--start-novis   or -sz : will start with no visualization"
    echo "--logs     or -l  : will display monitor.log for all robots"
    echo "--python   or -p  : will display python console for all robots"
    echo "Example: "
    echo ". starter.sh -r -s -l -p"
    exit 0
fi
source experimentconfig.sh

echo "+-----------------------------------------------------------+"
echo "MAINFOLDER IS $MAINFOLDER"

echo "+-----------------------------------------------------------+"
echo "Updating the ARGoS XML file"

envsubst < $ARGOSTEMPLATE > $ARGOSFILE

# echo "+-----------------------------------------------------------+"
# echo "Sending python scripts"
# cp -r $EXPERIMENTFOLDER/controllers/docker/* $DOCKERFOLDER/geth/python_scripts/

# echo "+-----------------------------------------------------------+"
# echo "Sending smart contracts"
# cp $SCFILE $TOYCHFOLDER/scs/deploy.py

echo "+-----------------------------------------------------------+"
echo "Cleaning logs folder..."

eval $(echo "rm -rf logs/{$(($NUMROBOTS+1))..100}")


# for opt in "$@"
# do
# if [[ $opt == "--reset" || $opt == "-r" ]]; then

#     echo "+-----------------------------------------------------------+"
#     echo "Resetting Geth..."
#     ./reset-geth
# fi
# done

# echo "+-----------------------------------------------------------+"
# echo "Waiting for web3 to respond..."

# ready=0
# while [[ $ready != $NUMROBOTS ]]; do
#     . test-tcp 4000
#     sleep 0.5
# done



echo "+-----------------------------------------------------------+"
echo "Starting Experiment"
echo "Arg: $@"
for opt in "$@"; do
    if [[ $opt == "--logs" || $opt == "-l" ]]; then
        ./tmux-all.sh -l monitor.log
    fi

    if [[ $opt == "--python" || $opt == "-p" ]]; then
        ./tmux-all.sh -s python
    fi

done

for opt in "$@"; do
    if [[ $opt == "--start" || $opt == "-s" ]]; then
        argos3 -c $ARGOSFILE
    fi

    if [[ $opt == "--start-novis" || $opt == "-sz" ]]; then
        argos3 -z -c $ARGOSFILE
    fi
done

