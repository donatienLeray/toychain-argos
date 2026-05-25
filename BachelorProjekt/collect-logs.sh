#!/bin/bash  
# Short script to extract log files from 
# DOCKERFOLDER/geth/logs and EXPERIMENTFOLDER/logs to
# EXPERIMENTFOLDER/results/data/experiment_name/config_name/rep

# Arguments: (string) experiment_name/config_name

source experimentconfig.sh

LOGSFOLDER="$EXPERIMENTFOLDER/logs/"
DATAFOLDER="$EXPERIMENTFOLDER/results/data/experiment_$1/"
EXPLORERDATAFOLDER="$MAINFOLDER/toychain/src/plugins/toychain-explorer/data"
LOCAL_EXPLORER_FOLDER="$EXPERIMENTFOLDER/logs/toychain_explorer"
PIDFILE="$EXPERIMENTFOLDER/logs/explorer.pid"

# Create the experiment directory
mkdir -p $LOGSFOLDER $DATAFOLDER

# Find the latest repetition in that folder
last_rep=$(ls $DATAFOLDER -v | tail -1 | sed 's/^0*//')
new_rep=$(printf "%03d\n" $(($last_rep+1)))

# Collect experiment configuration into /logs/
python3 << END
import sys, os

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.params import params as cp
from loop_functions.params import params as lp

# Collect the loop parameters
dict_list = [(param, value) for param, value in lp.items() if isinstance(value, dict)]

# Collect the control parameters
dict_list.extend([('control', cp)])

# Collect the experiment configuration
f = open('experimentconfig.sh', 'r')
experimentconfig = f.read()
experimentparams = {param:value for param,value in os.environ.items() if param in experimentconfig}
dict_list.extend([('experiment',experimentparams)])

savefile = open(os.environ['EXPERIMENTFOLDER'] + '/logs/config.py', 'w+')
for name, param_dict in dict_list:
  savefile.write('%s = %s \n' % (name, repr(param_dict)))
END

cp experimentconfig.sh $LOGSFOLDER
cp $EXPERIMENTFOLDER/loop_functions/params.py $LOGSFOLDER/loop_params.py
cp $EXPERIMENTFOLDER/controllers/params.py $LOGSFOLDER/control_params.py

## Prefer the newest observations.json between the per-experiment local
## folder and the plugin data folder. If both exist, choose the newer
## file by modification time. If only one exists, copy that one. When
## falling back to the plugin data folder, wait briefly for the server
## (if listed in $PIDFILE) to exit so it can write its final snapshot.
LOCAL_JSON="$LOCAL_EXPLORER_FOLDER/observations.json"
PLUGIN_JSON="$EXPLORERDATAFOLDER/observations.json"

if [ -f "$LOCAL_JSON" ] && [ -f "$PLUGIN_JSON" ]; then
  if [ "$LOCAL_JSON" -nt "$PLUGIN_JSON" ]; then
    cp -rp "$LOCAL_EXPLORER_FOLDER" "$LOGSFOLDER/toychain_explorer"
  else
    if [ -f "$PIDFILE" ]; then
      pid=$(cat "$PIDFILE" 2>/dev/null || true)
      if [ -n "$pid" ]; then
        for i in $(seq 1 20); do
          if ! kill -0 "$pid" 2>/dev/null; then
            break
          fi
          sleep 0.5
        done
      fi
    fi
    cp -rp "$EXPLORERDATAFOLDER" "$LOGSFOLDER/toychain_explorer"
  fi
elif [ -d "$LOCAL_EXPLORER_FOLDER" ]; then
  cp -rp "$LOCAL_EXPLORER_FOLDER" "$LOGSFOLDER/toychain_explorer"
elif [ -d "$EXPLORERDATAFOLDER" ]; then
  if [ -f "$PIDFILE" ]; then
    pid=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "$pid" ]; then
      for i in $(seq 1 20); do
        if ! kill -0 "$pid" 2>/dev/null; then
          break
        fi
        sleep 0.5
      done
    fi
  fi
  cp -rp "$EXPLORERDATAFOLDER" "$LOGSFOLDER/toychain_explorer"
fi

# # Collect geth related logs from docker folder into /logs/
# for ID in $(seq 1 $NUMROBOTS); do
#   cp -rp $DOCKERFOLDER/geth/logs/$ID/ $LOGSFOLDER
# done

# Collect data from /logs/ into /results/data
cp -rp $LOGSFOLDER $DATAFOLDER$new_rep

echo "Storing data to: /results/data/experiment_$1/$new_rep"