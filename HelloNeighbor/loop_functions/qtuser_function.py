#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random, math
import sys, os
import hashlib

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.actusensors.groundsensor import Resource
from controllers.utils import Vector2D
from controllers.params import params as cp
from loop_functions.params import params as lp

lp['generic']['show_rays'] = False
lp['generic']['show_pos'] = True
lp['generic']['tkuser'] = True

# /* Global Variables */
#######################################################################
rob_diam   = 0.07/2

# /* Global Functions */
#######################################################################
global robot, environment, tkuser

def hash_to_rgb(hash_value):
    # Generate a hash object from the input value
    hash_object = hashlib.sha256(hash_value.encode())

    # Get the first 3 bytes of the hash digest
    hash_bytes = hash_object.digest()[:3]

    # Convert the bytes to an RGB color value
    r = hash_bytes[0]
    g = hash_bytes[1]
    b = hash_bytes[2]

    # Return the RGB color value as a tuple
    return [r, g, b]

# /* tk_user Function */
#######################################################################

if lp['generic']['tkuser']:
    from loop_functions.tkuser_function import BlockchainGUI
    import threading

    def run_tkuser():
        global tkuser
        tkuser = BlockchainGUI()
        tkuser.start()

    tkuser_thread = threading.Thread(target=run_tkuser, daemon=True)
    tkuser_thread.start()


# /* ARGoS Functions */
#######################################################################

def init():
    pass
    
def draw_in_world():
    pass
	
def draw_in_robot():

    if "tkuser" in globals():
        prod_block = robot.variables.get_attribute("prod_block")
        if prod_block:
            tkuser.add_block(prod_block)


    # Draw block hash and state hash with circles
    color_state = hash_to_rgb(robot.variables.get_attribute("state_hash"))
    color_block = hash_to_rgb(robot.variables.get_attribute("block_hash"))
    color_mempl = hash_to_rgb(robot.variables.get_attribute("mempl_hash"))
    
    tx_count = int(robot.variables.get_attribute("mempl_size"))

    environment.qt_draw.circle([0,0,0.010], [], 0.100, color_state, True)
    environment.qt_draw.circle([0,0,0.011], [], 0.075, color_block, True)
    environment.qt_draw.circle([0,0,0.012+0.002*tx_count], [], 0.050, color_mempl, True)


def destroy():
    print('Closing the QT window')
