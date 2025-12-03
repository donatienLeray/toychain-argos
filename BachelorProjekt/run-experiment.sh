#!/bin/bash
# Iterate over experimental settings and start experiments
# Options:
# --tesst    or -t  : will run the experiment only once without collecting data
# --reset    or -r  : will reset everything blockchain related
# --start    or -s  : will start the experiment
# --startz   or -sz : will start with no visualization
# --logs     or -l  : will display monitor.log for all robots
# --python   or -p  : will display python console for all robots
# Example: 
# . starter.sh -r -s -l -p
print_usage() {
	echo " 
	Iterate over experimental settings and start experiments
	  Options:
	  --test    or -t  : will run the experiment only once without collecting data
	  --reset   or -r  : will reset everything blockchain related
	  --start   or -s  : will start the experiment
	  --startz  or -sz : will start with no visualization
	  --logs    or -l  : will display monitor.log for all robots
	  --python  or -p  : will display python console for all robots
	  Example:
	  . starter.sh -r -sz
	"
	exit 0
}

source ./experimentconfig.sh

DATAFOLDER="$EXPERIMENTFOLDER/results/data"

##################################################################################
### Set a value for any parameter in experimentconfig.sh
### USAGE:   config "parameter" value
### EXAMPLE: config "NUMROBOTS" 10 
config() {
	sed -i "s/^export ${1}=.*/export ${1}=${2}/" experimentconfig.sh
}

##################################################################################
### Set a value for any parameter in the loop_params.py dictionaries
### USAGE:   loopconfig "dictionary" "parameter" value
### EXAMPLE: loopconfig "patches" "radius" 0.05 
loopconfig() {
	sed -i "/\['${1}'\]\['${2}'\]/ s/=.*/= ${3}/" loop_functions/params.py
}

##################################################################################
### Copy a configuration from a previously run experiment in the results folder.
### USAGE:   copy "experimentName/configName"
### EXAMPLE: copy "test116_patchy/20_blockchain1"
copy() {
	# Collect the config from results
	cp $DATAFOLDER/experiment_${1}/001/experimentconfig.sh .
	cp $DATAFOLDER/experiment_${1}/001/controller_params.py controllers/
	cp $DATAFOLDER/experiment_${1}/001/loop_function_params.py loop_functions/
}

##################################################################################
### Copy a configuration from a previously run experiment in a remote server.
### USAGE:   import "experimentName/configName"
### EXAMPLE: import "test116_patchy/20_blockchain1"
import() {
	# Collect the config from results
	SSHHOST="eksander@esme"
	SSHSOCKET=~/.ssh/$SSHHOST
	
	ssh -M -f -N -o ControlPath=$SSHSOCKET $SSHHOST
	scp -o ControlPath=$SSHSOCKET $SSHHOST:$DATAFOLDER/experiment_${1}/001/experimentconfig.sh .
	scp -o ControlPath=$SSHSOCKET $SSHHOST:$DATAFOLDER/experiment_${1}/001/controller_params.py controllers/
	scp -o ControlPath=$SSHSOCKET $SSHHOST:$DATAFOLDER/experiment_${1}/001/loop_function_params.py loop_functions/
	ssh -S $SSHSOCKET -O exit $SSHHOST
}

##################################################################################
### Run an experiment for the number of repetitions given in experimentconfig.sh
### USAGE:   run "experimentName/configName"
### EXAMPLE: run "test116_patchy/20_blockchain1"
run() {

	# Configure experiment
	source ./experimentconfig.sh

	test_flag=false
	other_args=()

	for arg in "${@:2}"; do
	  case "$arg" in
	    -t|--test) test_flag=true ;;
		-h|--help) print_usage;;
	    *) other_args+=("$arg") ;;
	  esac
	done

	# If is a testrun
	if  [ "$test_flag" = true ]; then
		echo "Running test ${1}"
		bash starter.sh echo "${other_args[@]}"
		exit 0

	else
		for REP in $(seq 1 ${REPS}); do
			echo "Runing experiment ${1}"

			# Perform experiment
			bash starter.sh "${other_args[@]}"

			# Collect data
			if [ $# -ge 1 ]; then
			    bash collect-logs.sh ${1}
			fi
			
			echo "Completed repetition ${REP}/${REPS}"
			echo "-------------------------------------------------------------------"
		done
		echo "Completed experiment ${1}"
		echo "=============================================================================================="
	fi
}


# DEFINE EXPERIMENT
#EXP=vary_decay
#config "TPS" 30
#config "REPS" 1
#config "LENGTH" 500
#config "NOTES" "\"Variation of decay for hello_fixed_last lottery update from 50 to 500 \""
#loopconfig "scs" "lottery_update" "'hello_fixed_last'"
#
#for UTIL in $(seq 50 50 100); do 
#	CFG=${UTIL}
#	loopconfig "scs" "decay" "${UTIL}"
#	wait
#	run "${EXP}/${CFG}" $@
#done

# DEFINE EXPERIMENT
#EXP=vary_decay_on_poc
#config "TPS" 30
#config "REPS" 1
#config "LENGTH" 500
#config "NOTES" "\"Variation of decay for hello_fixed_last lottery update from 50 to 500 \""
#loopconfig "scs" "lottery_update" "'hello_fixed_last'"
#
#for UTIL in $(seq 10 10 50); do 
#	CFG=${UTIL}
#	loopconfig "scs" "decay" "${UTIL}"
#	wait
#	run "${EXP}/${CFG}" $@
#done


EXP=different_consensus_with_increasing_agents_2

# run experiment with different consensus mechanisms
for consensus in "ProofOfStake" "ProofOfWork"; do

	# standard values
	config "TPS" 30
	config "REPS" 1
	config "LENGTH" 500
	config "CONSENSUS" "$consensus"
	loopconfig "debug" "main" "False"
	loopconfig "debug" "loop" "True"

	# run experiment with increasing range of robots
	for UTIL in $(seq 30 5 50); do 
		#name of the configuration
		CFG=${consensus}_${UTIL}
		# set number of robots
		config "NUMROBOTS" "${UTIL}"
		# run experiment
		wait
		run "${EXP}/${CFG}" $@
	done

done




# # DEFINE CONFIGURATION 1
# CFG=linear_20
# 

# wait
# run    "${EXP}/${CFG}"


# DEFINE CONFIGURATION 1
# CFG=linear_20_limassign_0_regen_10
# config "LIMITASSIGN" 0
# config "NOTES" "\"Testing maxload 12 and new resource regen/forage; limassign 50 vs limassign 0; regen 5 vs regen 10\""

# wait
# run    "${EXP}/${CFG}"





# EXP=115_patch_size

# config "REPS" 3
# config "NUM1" 10

# #-----------------------
# config "SCNAME" "resource_market_limit" 
# config "MAXWORKERS" 2

# declare -a arr=(0.20 0.16 0.12 0.08 0.04)
# for patch_radius in "${arr[@]}"; do 
# 	loopconfig "patches" "radius" patch_radius	
# 	wait
# 	run    "${EXP}/limit_2" $1
# done	

# #-----------------------
# config "SCNAME" "resource_market_egreedy" 
# config "EPSILON" 50

# declare -a arr=(0.20 0.16 0.12 0.08 0.04)
# for patch_radius in "${arr[@]}"; do 
# 	loopconfig "patches" "radius" patch_radius	
# 	wait
# 	run    "${EXP}/egreedy_50" $1
# done

# #-----------------------
# config "SCNAME" "resource_market_egreedy"

# CFG=limit_3
# config "EPSILON" 50
# wait
# run    "${EXP}/${CFG}" $1

# CFG=egreedy_20
# config "EPSILON" 20
# wait
# run    "${EXP}/${CFG}"


# for EPSILON in $(seq 0 10 100); do 
# 	CFG=egreedy_${EPSILON}
# 	config "EPSILON" ${EPSILON}
# 	wait
# 	run    "${EXP}/${CFG}"
# done

exit 0
