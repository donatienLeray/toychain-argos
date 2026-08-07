#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import math
import sys, os, importlib
from ast import literal_eval

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]
argos_name= os.environ.get("ARGOSNAME", "").strip().lower()


from loop_functions.utils import hash_to_rgb
from controllers.utils import Vector2D
from controllers.actusensors.groundsensor import Resource
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
    print(f"No consensus module specified in loop_function params, defaulting to ProofOfAuthority")   
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
if argos_name == "foraging":
    res_diam   = 0.015
    res_height = 0.01

    # Store the position of the market and cache
    market   = Resource({"x":lp['market']['x'], "y":lp['market']['y'], "radius": lp['market']['r']})
    cache    = Resource({"x":lp['cache']['x'], "y":lp['cache']['y'], "radius": lp['cache']['r']})

# /* Global Functions */
#######################################################################
global robot, environment

#print Consensusmechanism and Smart Contract being used
print(f"Consensus Mechanism: {ConsensusClass.__name__}")
print(f"Smart Contract: {State.__name__}")


# /* foraging Functions */
#######################################################################

if argos_name == "foraging":
    def parse_robot_attr(attr_name, default):
        raw_value = robot.variables.get_attribute(attr_name)
        if not raw_value:
            return default
        try:
            return literal_eval(raw_value)
        except (ValueError, SyntaxError):
            return default
    
    def draw_market():
        environment.qt_draw.circle([market.x, market.y, 0.001],[], market.radius, 'custom2', True)
        environment.qt_draw.circle([cache.x, cache.y, 0.001],[], cache.radius, 'custom2', False)
    
    def draw_patches():
    
        with open(lp['files']['patches'], 'r') as f:
            allresources = [Resource(line) for line in f]
    
        for res in allresources:
            environment.qt_draw.circle([res.x, res.y, 0.001],[], res.radius, res.quality, False)
            environment.qt_draw.circle([res.x, res.y, 0.001],[], res.radius*(res.quantity/lp['patches']['qtty_max'][res.quality]), res.quality, True)
            environment.qt_draw.circle([res.x, res.y, 0.0005],[], res.radius, 'gray90', True)
    
        resources = parse_robot_attr("verified", [])
        for res in resources:
            x    = res[0]
            y    = res[1]
            json = res[2]
            environment.qt_draw.circle([x, y, 0.0003],[], lp['patches']['radii'][json['quality']]+0.03, json['quality'], False)
            environment.qt_draw.circle([x, y, 0.00025],[], lp['patches']['radii'][json['quality']]+0.03, 'black', True)
    
        resources = parse_robot_attr("pending", [])
        for res in resources:
            x    = res[0]
            y    = res[1]
            json = res[2]
            environment.qt_draw.circle([x, y, 0.0003],[], lp['patches']['radii'][json['quality']]+0.03, json['quality'], False)
            environment.qt_draw.circle([x, y, 0.00025],[], lp['patches']['radii'][json['quality']]+0.03, 'gray90', True)
    
        resources = parse_robot_attr("allpts", [])
        for res in resources:
            if len(res) < 3:
                continue

            all_x = res[0]
            all_y = res[1]
            json  = res[2]
            for x, y in zip(all_x, all_y):
                environment.qt_draw.circle([x, y, 0.0005],[], 0.02, 'black', True)
                environment.qt_draw.circle([x, y, 0.0005],[], 0.025, json['quality'], True)
    
    
    
    def draw_resources_on_robots():
        quantity = int(robot.variables.get_attribute("quantity") if robot.variables.get_attribute("quantity") else 0)
        quality  = robot.variables.get_attribute("hasResource")
    
    	# Draw carried quantity
    	# environment.qt_draw.cylinder([0, 0, 0.08],[], rob_diam * (quantity/cp[robot_type]['max_Q']), res_height, quality)
        for i in range(quantity):
            environment.qt_draw.cylinder([0, 0, (i*1.3)*res_height + 0.075],[], 0.5 * rob_diam, res_height, quality)


#######################################################################



def init():
    pass
    
def draw_in_world():
    if argos_name == "foraging":
        
        # Draw the Market
        draw_market()
        
        # Draw resource patches
        draw_patches()
	
def draw_in_robot():
        
    # Draw block hash and state hash with circles
    color_state = hash_to_rgb(robot.variables.get_attribute("state_hash"))
    color_block = hash_to_rgb(robot.variables.get_attribute("block_hash"))
    color_mempl = hash_to_rgb(robot.variables.get_attribute("mempl_hash"))
    if robot.variables.get_attribute("mempl_size") == '':
        tx_count = 0
    else:
        tx_count = int(robot.variables.get_attribute("mempl_size"))
        
    #environment.qt_draw.circle([0,0,0.010], [], 0.100, color_state, True) #outer circle #only intresting if state != block.state
    environment.qt_draw.circle([0,0,0.011], [], 0.075, color_block, True) #middle circle
    environment.qt_draw.circle([0,0,0.012], [], 0.050, color_mempl, True) #inner circle 
    
    
    
    if argos_name == "foraging":
        # Draw rays to w3 peers
        w3_peers = parse_robot_attr("w3_peers", [])
        for peer_rb in w3_peers:
            environment.qt_draw.ray([0, 0 , 0.01],[peer_rb[0]*math.cos(peer_rb[1]), peer_rb[0]*math.sin(peer_rb[1]) , 0.01], 'red', 0.15)
        # Draw ERB range
        erb_range  = robot.variables.get_attribute("erb_range") if robot.variables.get_attribute("erb_range") else 0
        environment.qt_draw.circle([0, 0, 0.00005],[], float(erb_range), 'gray90', False)
        # Draw resources carried by robots
        draw_resources_on_robots()
    
        #environment.qt_draw.box([3*rob_diam, 0, 0.005], [], [rob_diam, rob_diam, tx_count*0.5*rob_diam+0.0002], color_mempl)
    
        # Draw the Statesodometry position error
        odo_pos = Vector2D(parse_robot_attr("odo_position", [0, 0]))
        gps_pos = Vector2D(robot.position.get_position()[0:2])
        environment.qt_draw.circle(list(gps_pos-odo_pos)+[0.01],[], 0.025, 'blue', True)
        environment.qt_draw.ray([0,0,0.01], list(gps_pos-odo_pos)+[0.01], 'blue', 0.5)
   
    if argos_name == "obstacle":
        in_zone = robot.variables.get_attribute("in_zone") == "1"
        if in_zone:
                environment.qt_draw.circle([0,0,0.010], [], 0.100, [40, 200, 80], False)
        
    

    


def destroy():
    print('Closing the QT window')
