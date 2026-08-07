# [PATHS]
export HOMEFOLDER="$HOME"
export MAINFOLDER="$HOMEFOLDER/toychain-argos"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export TOYCHFOLDER="$MAINFOLDER/toychain"
export EXPERIMENTFOLDER="$MAINFOLDER/BachelorProjekt"
# [[ ":$PATH:" != *":$MAINFOLDER/scripts:"* ]] && export PATH=$PATH:$MAINFOLDER/scripts

# [SC]
export CONSENSUS=ProofOfConnection
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
export ARGOSNAME=foraging
export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.x.argos"
export CTRL=main_foraging.py
export CON1="${EXPERIMENTFOLDER}/controllers/${CTRL}"


export RABRANGE="0.5"
export WHEELNOISE="0"
export TPS=10
export DENSITY="2"
export AGENTSPEED=18
# True = all robots use the same speed, False = seeded symmetric pairs around AGENTSPEED
export SPEEDUNIFORM=True


#export NUMROBOTS=$(echo $NUM1+$NUM2 | bc)
export NUMROBOTS=5

# obstacle dimensions
export SCALINGF=$(echo "scale=3 ; sqrt($NUMROBOTS/5)" | bc)
export OBSTACLEB=$(echo "scale=3 ; 0.5*$SCALINGF" | bc)

# Arena dimension (obstacle arna needs to factor out the obstacle size, forage )
case "$ARGOSNAME" in
	"obstacle") export ARENADIM=$(echo "scale=3 ; 2.469*$SCALINGF" | bc) ;;
	*)          export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc) ;;
esac

export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)

# obstacle dimensions

export OBSTACLEL=$(echo "scale=3 ; 0.836*$SCALINGF" | bc)
export OBSTACLEOFFSET=$(echo "scale=3 ; $ARENADIMH-$OBSTACLEL/2" | bc)
export POINTDIM=$(echo "scale=3 ; $OBSTACLEB/sqrt(2)" | bc)
export POINTOFFSET=$(echo "scale=3 ; $ARENADIMH-$OBSTACLEL+$OBSTACLEB/2" | bc)
export POINTH=$(echo "scale=3 ; $OBSTACLEB/2" | bc)

# Top-right square side length in meters for entry/exit logging.
export ZONE_SIZE=$(echo "scale=3 ; $OBSTACLEL+$OBSTACLEB" | bc)

# Start 1/5 of the robots inside the triangle in a smaller square fully contained in it.
export TRIANGLE_ROBOTS=$(echo "scale=0 ; $NUMROBOTS/5" | bc)
export OUTSIDE_TRIANGLE_ROBOTS=$(echo "$NUMROBOTS-$TRIANGLE_ROBOTS" | bc)
export TRIANGLE_START_SIZE=$(echo "scale=3 ; $ZONE_SIZE/2" | bc)
export TRIANGLE_START_MIN=$(echo "scale=3 ; $ARENADIMH-$TRIANGLE_START_SIZE" | bc)

# Foraging specific parameters
export PATCHES_COUNT=$(echo "scale=0 ; $ARENADIM*15" | bc)
# export PATCHES_COUNT_B=$(echo "scale=0 ; $ARENADIM*25" | bc)


# [TOYCHAIN]
export BLOCKPERIOD=2
export EXPLORER=False
export EXPLORER_PATH="$TOYCHFOLDER/src/plugins/toychain-explorer/"
export EXPLORER_HOST="localhost"
export EXPLORER_PORT="8765"

# [OTHER]
export SEED=420
# When True, set SEED to the repetition number for each repetition
export REP_SEED=True
export TIMELIMIT=100
export LENGTH=400
export SLEEPTIME=5
export REPS=7
export NOTES="just a test"




