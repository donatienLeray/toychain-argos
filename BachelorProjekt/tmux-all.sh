#!/bin/bash
# Short script to open TMUX console with a pane for each robot or docker container
# Assumptions:
# - tmux is installed 
# - docker is running containers with names "${CONTAINERBASE}.{ID}"
#
# Options:
# -t list of robot IDs to tmux (string, e.g. "1 2 3 4")
# -n number of robots to tmux  (integer, e.g. 1)
# -s script to be executed     (string, bash, geth, python. Default: bash)
# -l logs to be displayed      (string, geth, monitor.log, sc.csv, estimate.csv, etc. Default: geth )


source experimentconfig.sh

tmux_ALL() {

	# Create an sequence of split window action for each container ID
	split_list=()
	for CT in "${ALL_CTS[@]:1}"; do
		ID=$(docker ps -f ID=$CT --format "{{.Names}}" | cut -d '.' -f2)
    split_list+=( split-pane docker exec -it "$CT" /bin/bash ';' select-layout even-vertical ';' )
	done

	# Open the terminal and configure it to execute docker bash
	gnome-terminal --geometry="$geom" --tab --title="$1" -- tmux new -s $1 docker exec -it "${ALL_CTS[0]}" /bin/bash ';' \
	    "${split_list[@]}" \
	    set-option -w synchronize-panes ';' \
		select-layout tiled ';' 
}

tmux_ALL_logs() {

	# Create an sequence of split window action for each robot ID
	split_list=()
	for ID in $(seq 2 $NUMROBOTS); do
	  split_list+=( split-pane tail -f "${EXPERIMENTFOLDER}"/logs/"${ID}"/"$2" ';' select-layout even-vertical ';' )
	done

	# Open the terminal and configure it to tail log files
	gnome-terminal --geometry="$geom" --tab --title="$1" -- tmux new -s $1 tail -f "${EXPERIMENTFOLDER}"/logs/"1"/"$2"  ';' \
	    "${split_list[@]}" \
	    set-option -w synchronize-panes ';' \
		select-layout tiled ';' 
}

tmux_ALL_geth_logs() {
	# Create an sequence of split window action for each container
	split_list=()
	for CT in "${ALL_CTS[@]:1}"; do
			ID=$(docker ps -f ID=$CT --format "{{.Names}}" | cut -d '.' -f2)
	    split_list+=( split-pane docker logs --tail 2000 --follow $CT ';' select-layout even-vertical ';' )
	done

	# Open the terminal and configure it to tail the docker logs
	gnome-terminal --geometry="$geom" --tab --title="$1" -- tmux new -s $1 docker logs --tail 2000 --follow "${ALL_CTS[0]}"  ';' \
	    "${split_list[@]}" \
	    set-option -w synchronize-panes ';' \
		select-layout tiled ';' 
}

# Define the terminal geometry (larger if there are many robots)
geom="default"
if [ $NUMROBOTS -gt 8 ]; then
	geomX=$(( $NUMROBOTS*15 ))
	geomY=$(( $NUMROBOTS*3 ))
	geom="${geomX}x${geomY}"
fi

TARGETS=""
SCRIPT=""
LOGS=""

while getopts ":n:t:s:l:" opt; do

  case ${opt} in
    t ) # process option t
			TARGETS=${OPTARG}
      ;;
    n ) # process option n
			NUMROBOTS=${OPTARG}
			;;
    s ) # process option s
			SCRIPT=${OPTARG}
      ;;
    l ) # process option l
			LOGS=${OPTARG}
      ;;
    \? ) echo "Usage: ./tmux-all.sh [-t] \"list of robot IDs\" [-n] (integer) [-s] (\"bash\" / \"python\" / \"geth\") [-l] (\"geth\" / \"monitor.log\" etc)"
      ;;
  esac
done

if [[ "$TARGETS" = "" ]]; then
	ALL_IDS=()
	ALL_CTS=()
	for ID in $(seq 1 $NUMROBOTS); do
		ALL_IDS+=(${ID})
		ALL_CTS+=($(docker ps -q -f name="${CONTAINERBASE}.${ID}\."))
	done

else
	ALL_IDS=()
	ALL_CTS=()
	for ID in $TARGETS; do
		ALL_IDS+=(${ID})
	  ALL_CTS+=($(docker ps -q -f name="${CONTAINERBASE}.${ID}\."))
	done
	NUMROBOTS=${#ALL_IDS[@]}

fi

echo "Target robots are:  $TARGETS"

if [[ "$SCRIPT" = "python" ]]; then 
	echo "Opening console: $SCRIPT "
	tmux kill-session -t PYTHON >/dev/null 2>&1
	tmux_ALL "PYTHON"
	tmux send-keys -t PYTHON "python3 -i /root/python_scripts/console.py" Enter

elif [[ "$SCRIPT" = "bash" ]]; then 
	echo "Opening console: $SCRIPT "
	tmux kill-session -t BASH >/dev/null 2>&1
	tmux_ALL "BASH"

elif [[ $SCRIPT = "geth" ]]; then
	echo "Opening console: $SCRIPT "
	tmux kill-session -t GETH >/dev/null 2>&1
 	tmux_ALL "GETH"
	tmux send-keys -t GETH "bash geth_attach.sh" Enter
fi



if [[ $LOGS = "monitor" ]]; then
	tmux kill-session -t LOGS >/dev/null 2>&1
	tmux_ALL_logs "LOGS" "monitor.log"

elif [[ $LOGS = "geth" ]]; then
	echo "Showing logs: $LOGS "
	tmux kill-session -t LOGS-GETH >/dev/null 2>&1
	tmux_ALL_geth_logs "LOGS-GETH"

elif [[ $LOGS != "" ]]; then
	tmux kill-session -t LOGS >/dev/null 2>&1
	tmux_ALL_logs "LOGS" $LOGS
fi	

