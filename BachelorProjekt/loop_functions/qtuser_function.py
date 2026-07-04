#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import sys, os, importlib, warnings

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from loop_functions.utils import hash_to_rgb
from loop_functions.params import params as lp
#-----------------------------
# toychain consensus mechanism
# import the correct consensus mechanism dynamically
if 'consensus' in lp and 'module' in lp['consensus']:
    module_name = "toychain.src.consensus." + lp['consensus']['module']
    module = importlib.import_module(module_name)
    ConsensusClass = getattr(module, lp['consensus']['class'])
    BLOCK_PERIOD = getattr(module, "BLOCK_PERIOD")
else: # default
    from toychain.src.consensus.ProofOfAuthority import ProofOfAuthority as ConsensusClass, BLOCK_PERIOD 
    warnings.showwarning(f"No consensus module specified in loop_function params, defaulting to ProofOfAuthority")   
# same as choosisng:
#from toychain.src.consensus.ProofOfConnection import ProofOfConnection , BLOCK_PERIOD
#from toychain.src.consensus.ProofOfAuth import ProofOfAuthority , BLOCK_PERIOD
#from toychain.src.consensus.ProofOfWork import ProofOfWork, BLOCK_PERIOD
#from toychain.src.consensus.ProofOfStake import ProofOfStake, BLOCK_PERIOD
#-----------------------------
#-----------------------------
# toychain State

# import the correct smart contract module dynamically
if 'scs' in lp and 'files' in lp['scs']:
    module_name = "scs." + lp['scs']['files']       
    module = importlib.import_module(module_name)
    State = getattr(module, "Contract") 
else: # default
    from scs.poa_w import Contract as State
#-----------------------------


# /* Global Variables */
#######################################################################
rob_diam   = 0.07/2
zone_border_color = [235, 180, 45]

# /* Global Functions */
#######################################################################
global robot, environment

#print Consensusmechanism and Smart Contract being used
print(f"Consensus Mechanism: {ConsensusClass.__name__}")
print(f"Smart Contract: {State.__name__}")

#######################################################################

def init():
    pass
    
def draw_in_world():

    arena_dim = float(lp['generic'].get('arena_dim', lp['generic'].get('arena_size')))
    zone_size = float(lp['generic'].get('zone_size', 0.5))
    arena_half = arena_dim / 2.0
    ax = arena_half
    ay = arena_half
    bx = max(-arena_half, arena_half - zone_size)
    by = arena_half
    cx = arena_half
    cy = max(-arena_half, arena_half - zone_size)

    z = 0.003

    def draw_edge(x0, y0, x1, y1):
        steps = max(6, int(zone_size / 0.04))
        for index in range(steps + 1):
            ratio = index / steps
            x = x0 + (x1 - x0) * ratio
            y = y0 + (y1 - y0) * ratio
            environment.qt_draw.circle([x, y, z], [], 0.007, zone_border_color, False)


    draw_edge(ax, ay, bx, by)
    draw_edge(ax, ay, cx, cy)
    draw_edge(bx, by, cx, cy)
	
def draw_in_robot():
    
    # Draw block hash and state hash with circles
    color_state = hash_to_rgb(robot.variables.get_attribute("state_hash"))
    color_block = hash_to_rgb(robot.variables.get_attribute("block_hash"))
    color_mempl = hash_to_rgb(robot.variables.get_attribute("mempl_hash"))
    in_zone = robot.variables.get_attribute("in_zone") == "1"
    
    if robot.variables.get_attribute("mempl_size") == '':
        tx_count = 0
    else:
        tx_count = int(robot.variables.get_attribute("mempl_size"))

    if in_zone:
        environment.qt_draw.circle([0,0,0.010], [], 0.100, [40, 200, 80], False)

    #environment.qt_draw.circle([0,0,0.010], [], 0.100, color_state, True) #outer circle #only intresting if state != block.state
    environment.qt_draw.circle([0,0,0.011], [], 0.075, color_block, True) #middle circle
    environment.qt_draw.circle([0,0,0.012], [], 0.050, color_mempl, True) #inner circle 


def destroy():
    print('Closing the QT window')
