# [PATHS]
export HOMEFOLDER="$HOME"
export MAINFOLDER="$HOMEFOLDER/toychain-argos"
export ARGOSFOLDER="$MAINFOLDER/argos-python"
export TOYCHFOLDER="$MAINFOLDER/toychain"
export EXPERIMENTFOLDER="$MAINFOLDER/RandomMarket_POS"
# [[ ":$PATH:" != *":$MAINFOLDER/scripts:"* ]] && export PATH=$PATH:$MAINFOLDER/scripts

# [FILES]
export ARGOSNAME="greeter"
export ARGOSFILE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.argos"
export ARGOSTEMPLATE="${EXPERIMENTFOLDER}/experiments/${ARGOSNAME}.x.argos"

# export CONTRACTADDRESS="${EXPERIMENTFOLDER}/scs/contractAddress.txt"
# export CONTRACTNAME="MarketForaging"
export SCNAME="greeter"
export SCFILE="${EXPERIMENTFOLDER}/scs/${SCNAME}.py" 
# export SCTEMPLATE="${EXPERIMENTFOLDER}/scs/${SCNAME}.x.py" 

export GENESISFILE="${DOCKERFOLDER}/geth/files/$GENESISNAME.json"

# [ARGOS]
export NUM1=9
export CON1="${EXPERIMENTFOLDER}/controllers/main.py"

export NUM2=0
export CON2="${EXPERIMENTFOLDER}/controllers/main_greedy.py"

export RABRANGE="0.5"
export WHEELNOISE="0"
export TPS=30
export DENSITY="2"

export NUMROBOTS=$(echo $NUM1+$NUM2 | bc)
export ARENADIM=$(echo "scale=3 ; sqrt($NUMROBOTS/$DENSITY)" | bc)
export ARENADIMH=$(echo "scale=3 ; $ARENADIM/2" | bc)
export STARTDIM=$(echo "scale=3 ; $ARENADIM/5" | bc)

# [GETH]
export BLOCKPERIOD=10

# [SC]
export MAXWORKERS=15
export LIMITASSIGN=2

export DEMAND_A=0
export DEMAND_B=1000
export REGENRATE=20
export FUELCOST=100
export QUOTA_temp=$(echo " scale=4 ; (75/$REGENRATE*$BLOCKPERIOD+0.05)/1" | bc)
export QUOTA=$(echo "$QUOTA_temp*10/1" | bc)
export QUOTA=200
export EPSILON=15
export WINSIZE=5

# [OTHER]
export SEED=1500
export TIMELIMIT=100
export LENGTH=100
export SLEEPTIME=5
export REPS=1
export NOTES="Variation of decay for hello_fixed_last lottery update from 50 to 500 "




