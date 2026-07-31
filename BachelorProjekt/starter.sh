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

generate_floor() {
    local floor_dir="$EXPERIMENTFOLDER/experiments/floors"
    local python_bin="${MAINFOLDER}/.venv-1/bin/python"

    if [ ! -x "$python_bin" ]; then
        python_bin="python3"
    fi

    echo "+-----------------------------------------------------------+"
    echo "Generating floor image for ARGOSNAME=$ARGOSNAME"
    ( cd "$floor_dir" && ARGOSNAME="$ARGOSNAME" "$python_bin" generate_floor.py )
}

cleanup_stale_argos_ports() {
    local base_port=1234
    local robot_count="${NUMROBOTS:-0}"

    if ! [[ "$robot_count" =~ ^[0-9]+$ ]] || [ "$robot_count" -le 0 ]; then
        return 0
    fi

    local end_port=$((base_port + robot_count - 1))
    local stale_pids

    if ! command -v ss >/dev/null 2>&1; then
        return 0
    fi

    stale_pids=$(ss -ltnp 2>/dev/null | awk -v b="$base_port" -v e="$end_port" '
        $1 == "LISTEN" && index($0, "\"argos3\"") > 0 {
            split($4, a, ":")
            p = a[length(a)] + 0
            if (p >= b && p <= e && match($0, /pid=[0-9]+/)) {
                pid = substr($0, RSTART + 4, RLENGTH - 4)
                print pid
            }
        }
    ' | sort -u)

    if [ -n "$stale_pids" ]; then
        echo "+-----------------------------------------------------------+"
        echo "Stopping stale ARGoS process(es) on robot ports ${base_port}-${end_port}: ${stale_pids}"
        kill $stale_pids 2>/dev/null || true
        sleep 1
    fi
}

echo "+-----------------------------------------------------------+"
echo "MAINFOLDER IS $MAINFOLDER"

echo "+-----------------------------------------------------------+"
echo "Updating the ARGoS XML file"

generate_floor

envsubst < $ARGOSTEMPLATE > $ARGOSFILE

# echo "+-----------------------------------------------------------+"
# echo "Sending python scripts"
# cp -r $EXPERIMENTFOLDER/controllers/docker/* $DOCKERFOLDER/geth/python_scripts/

echo "+-----------------------------------------------------------+"
echo "Sending smart contracts"
cp $SCFILE $TOYCHFOLDER/scs/deploy.py

echo "+-----------------------------------------------------------+"
echo "Cleaning logs folder..."

rm -rf logs/*

cleanup_stale_argos_ports

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

