#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import random
import sys, os
from unittest.mock import patch
import warnings
import json
import math
from collections import Counter as CCounter
#-----------------------------
mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]
#-----------------------------
# controllers
from MarketForaging.controllers.actusensors.movement     import RandomWalk, GPS, Navigate, OdoCompass
from MarketForaging.controllers.actusensors.groundsensor import ResourceVirtualSensor, Resource
from MarketForaging.controllers.actusensors.erandb       import ERANDB
from MarketForaging.controllers.actusensors.rgbleds      import RGBLEDs
from MarketForaging.controllers.utils import *
from MarketForaging.controllers.utils import FiniteStateMachine
from controllers.utils import hash_to_int
#-----------------------------
# Parameters
from controllers.params import params as cp
from loop_functions.params import params as lp
#-----------------------------
# helpers
from toychain.src.utils.helpers import gen_enode, enode_to_id
import importlib
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
    warnings.warn(f"No consensus module specified in loop_function params, defaulting to ProofOfAuthority")   
# same as choosisng:
#from toychain.src.consensus.ProofOfConnection import ProofOfConnection , BLOCK_PERIOD
#from toychain.src.consensus.ProofOfAuth import ProofOfAuthority , BLOCK_PERIOD
#from toychain.src.consensus.ProofOfWork import ProofOfWork, BLOCK_PERIOD
#from toychain.src.consensus.ProofOfStake import ProofOfStake, BLOCK_PERIOD
#-----------------------------
# toychain core modules
from toychain.src.Block import Block
from toychain.src.Node import Node
from toychain.src.Transaction import Transaction
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
global robot
# Robot ID (set in init)
global robotID
robotID = None

global startFlag
startFlag = False

global txList, tripList, submodules
txList, tripList, submodules = [], [], []

global clocks, counters, logs, txs
clocks, counters, logs, txs = dict(), dict(), dict(), dict()

# /* Experiment Global Variables */
#######################################################################

# Store the position of the market and cache
market   = Resource({"x":lp['market']['x'], "y":lp['market']['y'], "radius": lp['market']['r']})
cache    = Resource({"x":lp['cache']['x'], "y":lp['cache']['y'], "radius": lp['cache']['r']})


# intalise Genesis Block
#######################################################################
if ConsensusClass.__name__ == 'ProofOfAuthority' or ConsensusClass.__name__ == 'ProofOfWork':
    GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(lp['generic']['num_robots']))], 0, 0, 0, nonce = 1, state = State())
else:
    GENESIS = Block(0, 0000, [], 0, 0, 0, 0, nonce = 1, state = State())

# /* Logging Levels for Console and File */
#######################################################################
import logging
loglevel = 10
logtofile = False 

# /* Experiment State-Machine */
#######################################################################

class States(Enum):  
    EXPLORE  = 1
    NAVIGATE = 2
    FORAGE   = 3
    DROP     = 4
    
    
####################################################################################################################################################################################
#### INIT STEP #####################################################################################################################################################################
####################################################################################################################################################################################

def init():
    global clocks,counters, logs, submodules, me, rw, nav, odo, gps, rb, w3, fsm, rs, erb, rgb, robotID, robotSPEED, discovered, explore
    robotID = str(int(robot.variables.get_id()[2:])+1)
    robotIP = '127.0.0.1'
    robot.variables.set_attribute("id", str(robotID))
    robot.variables.set_attribute("circle_color", "gray50")
    robot.variables.set_attribute("block", "0")
    robot.variables.set_attribute("tdiff", "0")
    robot.variables.set_attribute("block_hash", str(hash("genesis")))
    robot.variables.set_attribute("state_hash", str(hash("genesis")))
    robot.variables.set_attribute("mempl_hash", str(hash("genesis")))
    robot.variables.set_attribute("mempl_size", "0")
    # special for foraging
    robot.variables.set_attribute("odo_position",repr(Vector2D()))
    robot.variables.set_attribute("scresources", "[]")
    robot.variables.set_attribute("scresources", "[]")
    robot.variables.set_attribute("foraging", "")
    robot.variables.set_attribute("dropResource", "")
    robot.variables.set_attribute("hasResource", "")
    robot.variables.set_attribute("resourceCount", "0")
    robot.variables.set_attribute("depleted", "")
    robot.variables.set_attribute("state", "")
    robot.variables.set_attribute("forageTimer", "0")
    robot.variables.set_attribute("quantity", "0")
    robot.variables.set_attribute("groupSize", "1")
    robot.variables.set_attribute("w3_peers", "[]")
    robot.variables.set_attribute("verified", "[]")
    robot.variables.set_attribute("pending", "[]")
    robot.variables.set_attribute("allpts", "[]")
    robot.variables.set_attribute("erb_range", str(cp['erbDist'] ))

    # /* Initialize Console Logging*/
    #######################################################################
    log_folder = experimentFolder + '/logs/' + robotID + '/'

    # Monitor logs (recorded to file)
    name =  'monitor.log'
    os.makedirs(os.path.dirname(log_folder+name), exist_ok=True) 
    logging.basicConfig(filename=log_folder+name, filemode='w+', format='[{} %(levelname)s %(name)s] %(message)s'.format(robotID))
    logging.getLogger('sc').setLevel(20)
    logging.getLogger('w3').setLevel(70)
    logging.getLogger('fsm').setLevel(10)
    
    robot.log = logging.getLogger(); 
    robot.log.setLevel(10)

    # /* Initialize submodules */
    #######################################################################

    # /* Init web3.py */
    robot.log.info('Initialising Python Geth Console...')
    #w3 = Node(robotID, robotIP, 1233 + int(robotID), ProofOfAuthority(genesis = GENESIS))
    w3 = Node(robotID, robotIP, 1233 + int(robotID), ConsensusClass(genesis = GENESIS),publish=True)
    robot.log.info(f'Consensus Mechanism: {ConsensusClass.__name__}')
    robot.log.info(f'Smart Contract: {State.__name__}')

    # /* Init an instance of peer for this Pi-Puck */
    me = Peer(robotID, robotIP, w3.enode, w3.key)
    
    #/* Init Resource-Sensors */
    robot.log.info('Initialising resource sensor...')
    rs = ResourceVirtualSensor(robot)

    # /* Init E-RANDB __listening process and transmit function
    robot.log.info('Initialising RandB board...')
    erb = ERANDB(robot, cp['erbDist'] , cp['erbtFreq'])
    
    # /* Init odometry sensor */
    robot.log.info('Initialising odometry...')
    robot.odo = OdoCompass(robot,variance=cp['error'])
    
    # get speed for this robot from the loop_function params
    agent_speeds = lp['generic'].get('agent_speeds', [])
    try:
        robot_idx = max(0, int(robotID) - 1)
    except Exception:
        robot_idx = 0

    if robot_idx < len(agent_speeds):
        robotSPEED = agent_speeds[robot_idx]
    else:
        robotSPEED = lp['generic']['agent_speed']

    robot.log.info(f'Random-walk speed: {robotSPEED}')
    
    # /* Init Random-Walk, __walking process */
    robot.log.info('Initialising random-walk...')
    rw = RandomWalk(robot, robotSPEED)
    
    # /* Init Navigation, __navigate process */
    robot.log.info('Initialising navigation...')
    nav = Navigate(robot, robotSPEED)

    # /* Init GPS sensor */
    robot.log.info('Initialising gps...')
    gps = GPS(robot)

    # /* Init LEDs */
    rgb = RGBLEDs(robot)

    # /* Init Finite-State-Machine */
    fsm = FiniteStateMachine(robot, start = States.EXPLORE)

    # List of submodules --> iterate .start() to start all
    submodules = [erb, rs, w3, robot.odo, fsm]

    # /* Initialize clocks*/
    #######################################################################
    
    clocks['peering']  = Timer(30)
    clocks['homing']   = Timer(50)
    clocks['explore']  = Timer(300)
    clocks['verify']   = Timer(0)
    clocks['block']    = Timer(BLOCK_PERIOD)
    
    # /* Initialize logmodules*/
    #######################################################################
    
    discovered = []
    explore = None
#########################################################################################################################
#### CONTROL STEP #######################################################################################################
#########################################################################################################################


def controlstep():
    global clocks, counters, startFlag, startTime, explore

    ###########################
    ######## ROUTINES #########
    ###########################

    def peering():

        # Get the current peers from erb if they have higher difficulty chain
        erb_enodes = {w3.gen_enode(peer.id) for peer in erb.peers if peer.getData(indices=[1,2]) > w3.get_total_difficulty() or peer.data[3] != w3.mempool_hash(astype='int')}
        
        # If using ProofOfConnection, update the smart contract with peer changes
        if ConsensusClass.__name__ == "ProofOfConnection" and lp['scs']['update'] != "none":
            # record Peers in the smart contract
            for peer in erb.peers:
                txdata = {'function': 'AddPeer', 'inputs': [peer.id]}
                tx = Transaction(sender = me.id, data = txdata, timestamp = w3.custom_timer.time())
                w3.send_transaction(tx)
        
                
        # Add peers on the toychain
        for enode in erb_enodes-set(w3.peers):
            try:
                w3.add_peer(enode)
                # log all peers
                logger.info(f"Robot {me.id} added peer {enode_to_id(enode)} at {w3.custom_timer.time()}")
            except Exception as e:
                raise e
            
        # Remove peers from the toychain
        for enode in set(w3.peers)-erb_enodes:
            try:
                w3.remove_peer(enode)
            except Exception as e:
                raise e

        # Turn on LEDs according to geth peer count
        rgb.setLED(rgb.all, rgb.presets.get(len(w3.peers), 3*['red']))
 
    def homing(resource):
 
        direction = (Vector2D(resource['x'],resource['y'])-market._pv).rotate(-25, degrees = True).normalize()
        target = direction*(market.radius+cache.radius)/2+market._pv
 
        nav.sensor = 'gps'
 
        # Navigate to drop location
        arrived = True
 
        if nav.get_distance_to(market._p) < market.radius + 0.5* (cache.radius-market.radius):
            nav.avoid(move = True)
        else:
            nav.navigate_with_obstacle_avoidance(target)
            arrived = False
         
        patch_gs = sensing()   
        if patch_gs:
            discovered.append({'x': patch_gs['json']['x'], 'y': patch_gs['json']['y']})
 
        nav.sensor = 'odometry'
 
        return arrived
 
    def sensing():
 
        # Sense environment for resources
        res = rs.getNew()
 
        if res:
            return {'x':res.x, 'y':res.y, 'json':json.loads(res._json)}
        
    
    def remove_patch_from_discovered(patch):
        # Remove a patch from the discovered list based on its coordinates
        for i, p in enumerate(discovered):
            if p.get("x") == patch['x'] and p.get("y") == patch['y']:
                discovered.pop(i)
                break
    
    def drop_if_passing_nest():
        if nav.get_distance_to(market._p) < market.radius + 0.5* (cache.radius-market.radius):
                    robot.variables.set_attribute("dropResource", "True")
                            
                    if not robot.variables.get_attribute("hasResource"):
                        robot.log.info(f"Dropped {robot.variables.get_attribute('quantity')}")
                        robot.variables.set_attribute("dropResource", "")  

  
    if not startFlag:
        ##########################
        #### FIRST STEP ##########
        ##########################

        startFlag = True 
        startTime = 0
        

        robot.log.info('--//-- Starting Experiment --//--')

        for module in [erb, rs, w3]:
            try:
                module.start()
            except:
                robot.log.critical('Error Starting Module: %s', module)
                sys.exit()

        for log in logs.values():
            log.start()

        for clock in clocks.values():
            clock.reset()

    else:

        ##############################
        ##### STATE-MACHINE STEP #####
        ##############################

        #########################################################################################################
        #### State::EVERY
        #########################################################################################################
        
        # Perform submodules step
        for module in [erb, rs, w3, robot.odo, fsm]:
            module.step()

        # Perform clock steps
        for clock in clocks.values():
            clock.time.step()

        if clocks['peering'].query():
            peering()
            
        # Updated odometry position
        robot.variables.set_attribute("odo_position",repr(robot.odo.getPosition()))
        
        if robot.variables.get_attribute("at") == "cache":
            robot.odo.setPosition()

        # Update blockchain state on the robot C++ object
        last_block = w3.get_block('last')
        robot.variables.set_attribute("block", str(last_block.height))
        robot.variables.set_attribute("tdiff", str(last_block.total_difficulty))
        robot.variables.set_attribute("prod_block", w3.get_produced_block())
        robot.variables.set_attribute("block_hash", str(last_block.hash))
        robot.variables.set_attribute("state_hash", str(last_block.state.state_hash))
        robot.variables.set_attribute("mempl_hash", w3.mempool_hash(astype='str'))
        robot.variables.set_attribute("mempl_size", str(len(w3.mempool)))

        erb.setData(hash_to_int(last_block.total_difficulty, 2), indices=[1,2])
        erb.setData(hash_to_int(w3.mempool_hash(astype='int'), 1), indices=[3]) 
            

        #########################################################################################################
        #### State::EXPLORE
        #########################################################################################################
        if fsm.query(States.EXPLORE):
            
            if explore is None:
                # 20% chance to explore, 80% chance to navigate to a discovered patch
                explore = random.random() <= 0.2
            
            # if there are discovered patches, navigate to the closest one
            if not explore and len(discovered) > 0:
                discovered.sort(key=lambda p: nav.get_distance_to((p['x'], p['y'])))
                robot.log.info(f"NAVIGATE to patch ({discovered[0]['x']},{discovered[0]['y']})")
                explore = None
                fsm.setState(States.NAVIGATE, message = "Switching to NAVIGATE", pass_along=discovered[0])  

            # Random walk
            rw.step()

            # Look for resources
            patch_gs = sensing()

            # Found resourcee forage
            if patch_gs:
                robot.log.info(f"Discovered {patch_gs['json'].get('quality','?')}")
                discovered.append({'x': patch_gs['json']['x'], 'y': patch_gs['json']['y']})
                fsm.setState(States.FORAGE, message = "Found patch", pass_along=patch_gs)
                
            drop_if_passing_nest()
            
        #########################################################################################################
        #### State::NAVIGATE
        #########################################################################################################
        if fsm.query(States.NAVIGATE):
            
            destination = fsm.pass_along

            # Navigate to resource
            distance = nav.navigate_with_obstacle_avoidance((destination['x'], destination['y']))
            
            # Sense for resources
            patch_gs = sensing()
            
            # found patch forage it
            if patch_gs:
                
                # patch is destination patch
                if(patch_gs['json']['x'], patch_gs['json']['y']) == (destination['x'], destination['y']):
                    robot.log.info(f"Arrived at patch ({destination['x']},{destination['y']})")
                    
                # Found new resourcee forage
                else:
                    robot.log.info(f"Discovered {patch_gs['json'].get('quality','?')}")
                    discovered.append({'x': patch_gs['json']['x'], 'y': patch_gs['json']['y']})
                
                fsm.setState(States.FORAGE, message = "Found patch", pass_along=patch_gs)
            # patch not found
            elif distance < 0.8*lp['patches']['radius']:
                remove_patch_from_discovered(destination)
                robot.log.info(f"Patch not found at ({destination['x']},{destination['y']})")
                fsm.setState(States.EXPLORE, message = "Patch not found")
                
            drop_if_passing_nest()

        #########################################################################################################
        #### State::FORAGE
        #########################################################################################################
        if fsm.query(States.FORAGE):
            
            # get patch information from the environment
            patch = sensing()
            
            # Current observed quantity for decision making
            try:
                current_q = int(patch['json'].get('quantity', 0))
            except Exception:
                current_q = 0

            # patch is empty
            depleted = current_q == 0 or patch is None
            # robot reached its capacity
            full = int(robot.variables.get_attribute("quantity")) >= cp['max_Q']
            
            # If patch is empty, remove it from discovered...
            if depleted:
                
                if patch is None:
                    # get the values from the passed along patch
                    patch=fsm.pass_along
                    
                remove_patch_from_discovered(patch)
                robot.log.info(f"Patch empty at ({patch['x']},{patch['y']});")
                robot.variables.set_attribute("foraging", "")
                
                # and if the robot still has capacity, go back to explore else go drop
                if int(robot.variables.get_attribute("quantity")) <= 0.5*cp['max_Q']:
                    fsm.setState(States.EXPLORE, message = "Patch empty", pass_along = patch)
                else:
                    robot.log.info(f"Capacity low ({robot.variables.get_attribute('quantity')}); heading to DROP")
                    fsm.setState(States.DROP, message = "Patch empty", pass_along = patch)
            
            # If robot reached its capacity, go drop
            if full:
                robot.log.info(f"Capacity reached ({robot.variables.get_attribute('quantity')}); heading to DROP")
                robot.variables.set_attribute("foraging", "")
                fsm.setState(States.DROP, message = f"Collected {robot.variables.get_attribute('quantity')} {patch['json'].get('quality','?')}", pass_along = patch)
            
            # if not depleted and not full, continue foraging
            if not depleted and not full:
                robot.variables.set_attribute("foraging", "True")
                nav.avoid(move = True)
                    

        #########################################################################################################
        #### State::DROP
        #########################################################################################################
        elif fsm.query(States.DROP):

            patch_to_drop = fsm.pass_along
            
            # Navigate home
            arrived = homing(patch_to_drop)
            
            if arrived:
                robot.variables.set_attribute("dropResource", "True")
            
            if not robot.variables.get_attribute("hasResource"):
                robot.log.info(f"Dropped {robot.variables.get_attribute('quantity')} {patch_to_drop['json'].get('quality','?')}")
                robot.variables.set_attribute("dropResource", "")
                explore = None   
                fsm.setState(States.EXPLORE, message = "Dropped: %s" % patch_to_drop['json']['quality'])    


#########################################################################################################################
#### RESET-DESTROY STEPS ################################################################################################
#########################################################################################################################

def reset():
    pass

def destroy():
    # Ensure we attempt to stop mining and then always try to write/close logs
    try:
        w3.stop_mining()
    except Exception as e:
        robot.log.exception(f"Failed to stop mining for robot {robotID}: {e}")

    try:
        txs_all = w3.get_all_transactions()
        if len(txs_all) != len(set([tx.id for tx in txs_all])):
            print(f'REPEATED TRANSACTIONS ON CHAIN: #{len(txs_all)-len(set([tx.id for tx in txs_all]))}')
    except Exception as e:
        robot.log.exception(f"Failed to fetch transactions for robot {robotID}: {e}")

    if lp['debug']['main']:
        try:
            for key, value in w3.sc.state.items():
                if key != 'connectivity' and key != 'lottery':
                    print(f"{key}: {value}")  
                    
            if "connectivity" in w3.sc.state:
                for key, value in w3.sc.state['connectivity'].items():
                    print(f"{enode_to_id(key)}: {value}")
                    
            elif "lottery" in w3.sc.state:
                for enode, count in CCounter(w3.sc.state['lottery']).items():
                    print(f"{enode_to_id(enode)}: {count}")
        except Exception as e:
            robot.log.exception(f"Failed to print debug state for robot {robotID}: {e}")

    # Make sure the log directory exists for this robot
    logdir = f"{experimentFolder}/logs/{robotID}"
    try:
        os.makedirs(logdir, exist_ok=True)
    except Exception as e:
        robot.log.exception(f"Failed to create log dir {logdir}: {e}")

    name   = 'block.csv'
    header = ['HEIGHT', 'MINER', 'BLOCK', 'TIMESTAMP', 'TELAPSED', 'RECEPTION', 'SIZE_KB', 'TXS', 'DIFF', 'TDIFF', 'HASH', 'PHASH']
    try:
        logs['block'] = Logger(f"{logdir}/{name}", header, ID = robotID)
    except Exception as e:
        robot.log.exception(f"Failed to open block log for robot {robotID}: {e}")
        logs['block'] = None

    name   = 'sc.csv'
    
    if lp['debug']['sc']:
        # Dynamically generate header from the genesis block's state attributes
        try:
            sc_header = list(GENESIS.state.__dict__.keys())
        except Exception:
            robot.log.warning(f"Failed to generate dynamic header for sc log for robot {robotID}, using fallback header")
            sc_header = ['n', 'private', 'balances']  # fallback
    # default header for PoC
    elif ConsensusClass.__name__ in ("ProofOfConnection","ProofOfStake"):
        sc_header = ['n', 'private', 'balances', 'connectivity'] 
    # default header for PoS and PoA
    else:
        sc_header = ['n', 'private', 'balances']
    
    try:
        logs['sc'] = Logger(f"{logdir}/{name}", sc_header, ID = robotID)
    except Exception as e:
        robot.log.exception(f"Failed to open sc log for robot {robotID}: {e}")
        logs['sc'] = None

    # Log each block over the operation of the swarm
    try:
        for block in w3.chain:
            if logs.get('block'):
                try:
                    logs['block'].log(
                        [block.height,                           # HEIGHT
                         block.miner_id,                         # MINER
                         block.number,                           # BLOCK
                         block.timestamp,                        # TIMESTAMP
                         0 if block.reception == 0 else block.reception - block.timestamp,      # TELAPSED
                         block.reception,                        # RECEPTION
                         sys.getsizeof(block) / 1024,            # SIZE (KB)
                         len(block.data),                        # TXS
                         block.difficulty,                       # DIFF
                         block.total_difficulty,                 # TDIFF
                         block.hash,                             # HASH
                         block.parent_hash,                      # PHASH
                        ])
                except Exception as e:
                    robot.log.exception(f"Failed to write to block log for robot {robotID}: {e}")

            if logs.get('sc'):
                try:
                    # Dynamically get values from state attributes matching the header
                    sc_values = [getattr(block.state, attr, None) for attr in sc_header]
                    logs['sc'].log(sc_values)
                except Exception as e:
                    robot.log.exception(f"Failed to write to sc log for robot {robotID}: {e}")
                    
    except Exception as e:
        robot.log.exception(f"Failed while iterating chain for robot {robotID}: {e}")
    finally:
        # Ensure logs are flushed and closed
        try:
            if logs.get('block'):
                logs['block'].file.flush()
                try:
                    os.fsync(logs['block'].file.fileno())
                except Exception:
                    pass
                logs['block'].close()
        except Exception as e:
            robot.log.exception(f"Failed to close block log for robot {robotID}: {e}")
        try:
            if logs.get('sc'):
                logs['sc'].file.flush()
                try:
                    os.fsync(logs['sc'].file.fileno())
                except Exception:
                    pass
                logs['sc'].close()
        except Exception as e:
            robot.log.exception(f"Failed to close sc log for robot {robotID}: {e}")

    # Print which robot was killed
    try:
        print('Killed robot '+ robotID)
    except Exception:
        print('Killed robot')

#########################################################################################################################
#########################################################################################################################
#########################################################################################################################

