#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random
import time, sys, os

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.utils import Vector2D, Logger, Timer, Accumulator, mydict, identifiersExtract
from controllers.params import params as cp
from loop_functions.params import params as lp
from loop_functions.utils import *

from controllers.actusensors.groundsensor import Resource

random.seed(lp['generic']['seed'])

log_folder = lp['environ']['EXPERIMENTFOLDER'] + '/logs/0/'
os.makedirs(os.path.dirname(log_folder), exist_ok=True)   

# /* Global Variables */
#######################################################################
global startFlag, stopFlag, startTime
startFlag = False
stopFlag = False
startTime = 0

# Initialize RAM and CPU usage
global RAM, CPU
RAM = getRAMPercent()
CPU = getCPUPercent()
TPS = int(lp['environ']['TPS'])

# Initialize timers/accumulators/logs:
global clocks, accums, logs, other
clocks, accums, logs, other = dict(), dict(), dict(), dict()

clocks['simlog'] = Timer(10*TPS)
clocks['block']      = Timer(15*TPS)

global allrobots

# debug variables
global step_count
step_count = 0

def init():
   
    # Init logfiles for loop function
    file   = 'simulation.csv'
    header = ['TPS', 'RAM', 'CPU']
    logs['simulation'] = Logger(log_folder+file, header, ID = '0')

    file   = 'loop.csv'
    header = []
    logs['loop'] = Logger(log_folder+file, header, ID = '0')

    for log in logs.values():
        log.start()

def pre_step():
    global startFlag, startTime

    # Tasks to perform on the first time step
    if not startFlag:
        startTime = 0

def post_step():
    global startFlag, clocks, accums
    global RAM, CPU
    global step_count

    if not startFlag:
        startFlag = True

    # Logging of simulation simulation (RAM, CPU, TPS)   
    if clocks['simlog'].query():
        RAM = getRAMPercent()
        CPU = getCPUPercent()
    TPS = round(1/(time.time()-logs['simulation'].latest))
    logs['simulation'].log([TPS, CPU, RAM])

    # Logging of loop function variables
    logs['loop'].log([])
    
    # print loading bar with ETA
    if lp['debug']['loop']:
        total_steps = int(os.environ['TPS']) * int(os.environ['LENGTH'])
        loading_bar(total_steps, step_count, TPS=TPS)
    step_count += 1

def is_experiment_finished():
    pass

def reset():
    pass

def destroy():
    pass

def post_experiment():
    print("Finished from Python!")
    # Don't kill argos process abruptly; allow ARGoS to shutdown gracefully.
    # If you really need to force-kill Argos at the end of the experiment, enable it via
    # environment variable KILL_ARGOS=True
    if os.environ.get('KILL_ARGOS', 'False') in ['True', 'true', '1']:
        os.system('pkill argos3')
    else:
        # Let ARGoS exit on its own.
        pass




