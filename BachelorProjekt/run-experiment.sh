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

# optionally set seed to REP*42 if REP_SEED is enabled
		if [ "${REP_SEED}" = "True" ] || [ "${REP_SEED}" = "true" ] || [ "${REP_SEED}" = "1" ]; then
			# compute seed as repetition number multiplied by 42
			SEEDVAL=$((REP * 42))
			config "SEED" ${SEEDVAL}
			echo "Setting SEED=${SEEDVAL}"
		fi

			# Perform experiment
			# Ensure explorer port is free (stop any local explorer process owned by this user)
			if [ -n "${MAINFOLDER-}" ] && [ -x "${MAINFOLDER}/tools/stop_explorer_safe.sh" ]; then
				${MAINFOLDER}/tools/stop_explorer_safe.sh --kill 8765 || true
			elif [ -x "../tools/stop_explorer_safe.sh" ]; then
				../tools/stop_explorer_safe.sh --kill 8765 || true
			fi

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

####################################################################
########################## TESTS ###################################
####################################################################

## run experiment with different consensus mechanisms
#EXP=test
#CFG=test
#
## Explorer
#config "EXPLORER" "False"
#
## standard values
#config "TPS" 10
#config "REPS" 20
#config "LENGTH" 400
#config "REP_SEED" "True"
#loopconfig "debug" "main" "False"
#loopconfig "debug" "loop" "True"
#loopconfig "debug" "scs" "True"
#config "AGENTSPEED" 18
## set to to false for experiment 2_random_walk_different_speed
#config "SPEEDUNIFORM" "True"
## set to obstacle for experiment 3_random_walk_obstacle_trap else set to greeter
#config ARGOSNAME "foraging" #greeter|obstacle|foraging
## set the cotroller to main_foraging.py for experiment 4_foragingelse set to main
#config "CTRL" "main_foraging.py" #main|main_foraging.py
#config "CONSENSUS" "ProofOfAuthority"
#loopconfig "scs" "update" "\"no_update\""
#loopconfig "scs" "decay" 50
#
## set number of robots
#config "NUMROBOTS" 15
#patches_m=$(( 15*5))
#loopconfig "patches" "counts" "{'red': 0, 'green': 0, 'blue': ${patches_m}, 'yellow': 0}"
## run experiment
#wait
#run "${EXP}/${CFG}" $@

####################################################################
################### ALL EXPERIMENTS  ###############################
####################################################################

# For alll experiments

# Meta parameters
config "TPS" 10
config "REPS" 7
config "LENGTH" 400
config "REP_SEED" "True"

# Debugging
config "EXPLORER" "False" #to see life blockchain explorer.
loopconfig "debug" "main" "False"
loopconfig "debug" "loop" "True"
loopconfig "debug" "scs" "True"
# agent configuration
config "AGENTSPEED" 18


#####################################################################
#EXP=1_random_walk
#####################################################################
#
## set to to false for experiment 2_random_walk_different_speed
#config "SPEEDUNIFORM" "True"
## set to obstacle for experiment 3_random_walk_obstacle_trap else set to greeter
#config ARGOSNAME "greeter" #greeter|obstacle|foraging
## set the cotroller to main_foraging.py for experiment 4_foragingelse set to main
#config "CTRL" "main.py" #main|main_foraging.py
#
##########
## R-POA #
##########
#config "CONSENSUS" "ProofOfConnection"
#loopconfig "scs" "update" "\"no_update\""
#loopconfig "scs" "decay" 50
#
## run experiment with increasing range of robots
#for UTIL in $(seq 5 5 25); do 
#	#name of the configuration
#	CFG="R-PoA_${UTIL}"
#	# set number of robots
#	config "NUMROBOTS" "${UTIL}"
#	# run experiment
#	wait
#	run "${EXP}/${CFG}" $@
#done
#
###################
### POA,PoW & PoC #
###################
#loopconfig "scs" "update" "\"peer_index\""
#for consensus in "ProofOfAuthority" "ProofOfWork" "ProofOfConnection"; do
#  	config "CONSENSUS" "$consensus"
#
#	# run experiment with increasing range of robots
#	for UTIL in $(seq 5 5 25); do 
#		#name of the configuration using switch case for consensus name
#		case "$consensus" in
#			"ProofOfAuthority") CFG="PoA_${UTIL}" ;;
#			"ProofOfWork") CFG="PoW_${UTIL}" ;;
#			"ProofOfConnection") CFG="C-PoA_${UTIL}" ;;
#			*) CFG="${consensus}_${UTIL}" ;;
#		esac
#		# set number of robots
#		config "NUMROBOTS" "${UTIL}"
#		# run experiment
#		wait
#		run "${EXP}/${CFG}" $@
#	done
#
#done

#####################################################################
#EXP=2_random_walk_different_speed
#####################################################################
#
## Explorer
#config "EXPLORER" "False"
#
## set to to false for experiment 2_random_walk_different_speed
#config "SPEEDUNIFORM" "False"
## set to obstacle for experiment 3_random_walk_obstacle_trap else set to greeter
#config ARGOSNAME "greeter" #greeter|obstacle|foraging
## set the cotroller to main_foraging.py for experiment 4_foragingelse set to main
#config "CTRL" "main.py" #main|main_foraging.py
#
##########
## R-POA #
##########
#config "CONSENSUS" "ProofOfConnection"
#loopconfig "scs" "update" "\"no_update\""
#loopconfig "scs" "decay" 50
#
## run experiment with increasing range of robots
#for UTIL in $(seq 5 5 25); do 
#	#name of the configuration
#	CFG="R-PoA_${UTIL}"
#	# set number of robots
#	config "NUMROBOTS" "${UTIL}"
#	# run experiment
#	wait
#	run "${EXP}/${CFG}" $@
#done
#
###################
### POA,PoW & PoC #
###################
#loopconfig "scs" "update" "\"peer_index\""
#for consensus in "ProofOfAuthority" "ProofOfWork" "ProofOfConnection"; do
#  	config "CONSENSUS" "$consensus"
#
#	# run experiment with increasing range of robots
#	for UTIL in $(seq 5 5 25); do 
#		#name of the configuration using switch case for consensus name
#		case "$consensus" in
#			"ProofOfAuthority") CFG="PoA_${UTIL}" ;;
#			"ProofOfWork") CFG="PoW_${UTIL}" ;;
#			"ProofOfConnection") CFG="C-PoA_${UTIL}" ;;
#			*) CFG="${consensus}_${UTIL}" ;;
#		esac
#		# set number of robots
#		config "NUMROBOTS" "${UTIL}"
#		# run experiment
#		wait
#		run "${EXP}/${CFG}" $@
#	done
#
#done

#####################################################################
#EXP=3_random_walk_obstacle_trap
#####################################################################
#
## set to to false for experiment 2_random_walk_different_speed
#config "SPEEDUNIFORM" "True"
## set to obstacle for experiment 3_random_walk_obstacle_trap else set to greeter
#config ARGOSNAME "obstacle" #greeter|obstacle|foraging
## set the cotroller to main_foraging.py for experiment 4_foragingelse set to main
#config "CTRL" "main.py" #main|main_foraging.py
#
##########
## R-POA #
##########
#config "CONSENSUS" "ProofOfConnection"
#loopconfig "scs" "update" "\"no_update\""
#loopconfig "scs" "decay" 50
#
## run experiment with increasing range of robots
#for UTIL in $(seq 5 5 25); do 
#	#name of the configuration
#	CFG="R-PoA_${UTIL}"
#	# set number of robots
#	config "NUMROBOTS" "${UTIL}"
#	# run experiment
#	wait
#	run "${EXP}/${CFG}" $@
#done
#
###################
### POA,PoW & PoC #
###################
#loopconfig "scs" "update" "\"peer_index\""
#for consensus in "ProofOfAuthority" "ProofOfWork" "ProofOfConnection"; do
#  	config "CONSENSUS" "$consensus"
#
#	# run experiment with increasing range of robots
#	for UTIL in $(seq 5 5 25); do 
#		#name of the configuration using switch case for consensus name
#		case "$consensus" in
#			"ProofOfAuthority") CFG="PoA_${UTIL}" ;;
#			"ProofOfWork") CFG="PoW_${UTIL}" ;;
#			"ProofOfConnection") CFG="C-PoA_${UTIL}" ;;
#			*) CFG="${consensus}_${UTIL}" ;;
#		esac
#		# set number of robots
#		config "NUMROBOTS" "${UTIL}"
#		# run experiment
#		wait
#		run "${EXP}/${CFG}" $@
#	done
#
#done


####################################################################
EXP=4_foraging	
####################################################################

# set to to false for experiment 2_random_walk_different_speed
config "SPEEDUNIFORM" "True"
# set to obstacle for experiment 3_random_walk_obstacle_trap else set to greeter
config ARGOSNAME "foraging" #greeter|obstacle|foraging
# set the cotroller to main_foraging.py for experiment 4_foragingelse set to main
config "CTRL" "main_foraging.py" #main|main_foraging.py

#########
# R-POA #
#########
config "CONSENSUS" "ProofOfConnection"
loopconfig "scs" "update" "\"no_update\""
loopconfig "scs" "decay" 50

# run experiment with increasing range of robots
for UTIL in $(seq 5 5 25); do 
	#name of the configuration
	CFG="R-PoA_${UTIL}"
	# set number of robots
	config "NUMROBOTS" "${UTIL}"
	# run experiment
	wait
	run "${EXP}/${CFG}" $@
done

##################
## POA,PoW & PoC #
##################
loopconfig "scs" "update" "\"peer_index\""
for consensus in "ProofOfAuthority" "ProofOfWork" "ProofOfConnection"; do
  	config "CONSENSUS" "$consensus"

	# run experiment with increasing range of robots
	for UTIL in $(seq 5 5 25); do 
		#name of the configuration using switch case for consensus name
		case "$consensus" in
			"ProofOfAuthority") CFG="PoA_${UTIL}" ;;
			"ProofOfWork") CFG="PoW_${UTIL}" ;;
			"ProofOfConnection") CFG="C-PoA_${UTIL}" ;;
			*) CFG="${consensus}_${UTIL}" ;;
		esac
		# set number of robots
		config "NUMROBOTS" "${UTIL}"
		# run experiment
		wait
		run "${EXP}/${CFG}" $@
	done

done


#####################################################################
exit 0
