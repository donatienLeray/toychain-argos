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

rm -rf logs/*

if [ "$EXPLORER" = "True" ]; then
    unset TOYCHAIN_EXPLORER_LOCAL_DIR
else
    export TOYCHAIN_EXPLORER_LOCAL_DIR="$EXPERIMENTFOLDER/logs/toychain_explorer"
    mkdir -p "$TOYCHAIN_EXPLORER_LOCAL_DIR"
fi

if [ "$EXPLORER" = "True" ]; then
    echo "+-----------------------------------------------------------+"
    echo "Starting Toychain explorer at http://${EXPLORER_HOST}:${EXPLORER_PORT}"
    echo "+-----------------------------------------------------------+"

    python3 "$EXPLORER_PATH/server.py" --host "$EXPLORER_HOST" --port "$EXPLORER_PORT" &

    EXPLORER_PID=$!
    # record pid so other scripts can detect the running explorer
    echo "$EXPLORER_PID" > "$EXPERIMENTFOLDER/logs/explorer.pid"
    # on exit, terminate explorer and wait for it to finish (so snapshot is written)
    trap "kill $EXPLORER_PID 2>/dev/null; wait $EXPLORER_PID 2>/dev/null || true; rm -f '$EXPERIMENTFOLDER/logs/explorer.pid' 2>/dev/null" EXIT
fi



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

