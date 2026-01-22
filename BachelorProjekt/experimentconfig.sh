# [PATHS]
export HOMEFOLDER="$HOME"
export MAINFOLDER="$HOMEFOLDER/toychain-argos"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export TOYCHFOLDER="$MAINFOLDER/toychain"
export EXPERIMENTFOLDER="$MAINFOLDER/BachelorProjekt"
# [[ ":$PATH:" != *":$MAINFOLDER/scripts:"* ]] && export PATH=$PATH:$MAINFOLDER/scripts

# [SC]
export CONSENSUS=ProofOfAuthority
case "$CONSENSUS" in
	"ProofOfAuthority")  export SCNAME="poa_w" ;;
	"ProofOfConnection") export SCNAME="poc" ;;
	"ProofOfWork")       export SCNAME="poa_w" ;;
	"ProofOfStake")      export SCNAME="pos" ;;
	*)                    #errormessage
		echo "Unknown consensus mechanism: $CONSENSUS"
		exit 1
		;;
esac
export SCFILE="${EXPERIMENTFOLDER}/scs/${SCNAME}.py" 
export GENESISFILE="${DOCKERFOLDER}/geth/files/$GENESISNAME.json"


# [ARGOS]
export ARGOSNAME="greeter"
export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.x.argos"

#export NUM1=15
export CON1="${EXPERIMENTFOLDER}/controllers/main.py"

#export NUM2=0
#export CON2="${EXPERIMENTFOLDER}/controllers/main_greedy.py"

export RABRANGE="0.5"
export WHEELNOISE="0"
export TPS=10
export DENSITY="2"

#export NUMROBOTS=$(echo $NUM1+$NUM2 | bc)
export NUMROBOTS=25
export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc)
export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)

# [GETH]
export BLOCKPERIOD=1
export RUN_TKUSER="False"

# [OTHER]
export SEED=420
# When True, set SEED to the repetition number for each repetition
export REP_SEED=True
export TIMELIMIT=100
export LENGTH=400
export SLEEPTIME=5
export REPS=10
export NOTES="just a test"




