#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import sys, os, importlib, warnings

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from loop_functions.utils import hash_to_rgb
from loop_functions.params import params as lp
from toychain.src.utils.helpers import gen_enode
from toychain.src.Node import Node
from toychain.src.Block import Block
#-----------------------------
# toychain consensus mechanism
# import the correct consensus mechanism dynamically
if 'consensus' in lp and 'module' in lp['consensus']:
    module_name = "toychain.src.consensus." + lp['consensus']['module']
    module = importlib.import_module(module_name)
    ConsensusClass = getattr(module, lp['consensus']['class'])
    BLOCK_PERIOD = getattr(module, "BLOCK_PERIOD")
else: # default
    from toychain.src.consensus.ProofOfAuth import ProofOfAuthority as ConsensusClass, BLOCK_PERIOD 
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


lp['generic']['show_rays'] = False
lp['generic']['show_pos'] = True

# /* Global Variables */
#######################################################################
rob_diam   = 0.07/2

# /* Global Functions */
#######################################################################
global robot, environment

enodes = [gen_enode(i+1) for i in range(int(lp['environ']['NUMROBOTS']))]

#initialize glassnode Genesis Block
GENESIS = Block(0, 0000, [], 0, 0, 0, 0, nonce = 1, state = State())


glassnode = Node('0', '127.0.0.1', 1233, ConsensusClass(genesis = GENESIS))
#######################################################################

def init():
    pass
    
def draw_in_world():

    # Update glassnode
	glassnode.step()
	if glassnode.custom_timer.time() == 10:
		glassnode.add_peers(enodes)
		glassnode.start()
		glassnode.run_explorer()
	
def draw_in_robot():
    
    # Draw block hash and state hash with circles
    color_state = hash_to_rgb(robot.variables.get_attribute("state_hash"))
    color_block = hash_to_rgb(robot.variables.get_attribute("block_hash"))
    color_mempl = hash_to_rgb(robot.variables.get_attribute("mempl_hash"))
    
    if robot.variables.get_attribute("mempl_size") == '':
        tx_count = 0
    else:
        tx_count = int(robot.variables.get_attribute("mempl_size"))

    environment.qt_draw.circle([0,0,0.010], [], 0.100, color_state, True)
    environment.qt_draw.circle([0,0,0.011], [], 0.075, color_block, True)
    environment.qt_draw.circle([0,0,0.012+0.002*tx_count], [], 0.050, color_mempl, True)


def destroy():
    print('Closing the QT window')
